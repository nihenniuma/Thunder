# -*- coding: utf-8 -*-
import os
import re
import math
from time import time, sleep
from collections import Counter
# upgrade numpy with: "pip install numpy --upgrade"
import numpy as np


# These parameter were minimized by the evolutionary algorithm
# https://github.com/ChristophSchranz/Tweaker-3_optimize-using-ea, branch ea-optimize_20200414' on 100 objects
# with a fitness of 5.10246, and a miss-classification rate of 4.0
PARAMETER = {
    "TAR_A": 0.023251193283878126,
    "TAR_B": 0.17967732044591803,
    "RELATIVE_F": 11.250931864115714,
    "CONTOUR_F": 0.219523237806102,
    "BOTTOM_F": 1.3206227038470124,
    "TAR_C": -0.016564249433447253,
    "TAR_D": 1.0592490333488807,
    "TAR_E": 0.011503545133447014,
    "FIRST_LAY_H": 0.04754881938390257,
    "VECTOR_TOL": -0.0008385913582234466,
    "NEGL_FACE_SIZE": 0.4737309463791554,
    "ASCENT": -0.07809801382985776,
    "PLAFOND_ADV": 0.059937025927212395,
    "CONTOUR_AMOUNT": 0.018242751444131886,
    "OV_H": 2.574100894603089,
    "height_offset": 2.372824083342488,
    "height_log": 0.04137517666768212,
    "height_log_k": 1.9325457851679673
}
# https://github.com/ChristophSchranz/Tweaker-3_optimize-using-ea, branch ea-optimize_20200427_vol' on 100 objects
# with a fitness of 4.06166, and a miss-classification rate of 3.5
PARAMETER_VOL = {
    "TAR_A": 0.012826785357111374,
    "TAR_B": 0.1774847296275851,
    "RELATIVE_F": 6.610621027964314,
    "CONTOUR_F": 0.23228623269775997,
    "BOTTOM_F": 1.167152017941474,
    "TAR_C": 0.24308070476924726,
    "TAR_D": 0.6284515508160871,
    "TAR_E": 0.032157292647062234,
    "FIRST_LAY_H": 0.029227991916155015,
    "VECTOR_TOL": -0.0011163303070972383,
    "NEGL_FACE_SIZE": 0.4928696161029859,
    "ASCENT": -0.23897449119622627,
    "PLAFOND_ADV": 0.04079208948120519,
    "CONTOUR_AMOUNT": 0.0101472219892684,
    "OV_H": 1.0370178217794535,
    "height_offset": 2.7417608343142073,
    "height_log": 0.06442030687034085,
    "height_log_k": 0.3933594673063997
}


class Tweak:
    """ The Tweaker is an auto rotate class for 3D objects.

    The critical angle CA is a variable that can be set by the operator as
    it may depend on multiple factors such as material used, printing
     temperature, printing speed, etc.

    Following attributes of the class are supported:
    The tweaked z-axis'.
    Euler coords .v and .phi, where v is orthogonal to both z and z' and phi
     the angle between z and z' in rad.
    The rotational matrix .Matrix, the new mesh is created by multiplying each
     vector with R.
    And the relative unprintability of the tweaked object. If this value is
     greater than 10, a support structure is suggested.
    """

    def __init__(self, content, extended_mode=False, verbose=True, show_progress=False,
                 favside=None, min_volume=False, parameter=None,  progress_callback=None):
        # Load parameters
        if parameter is None:
            if min_volume:
                parameter = PARAMETER_VOL
            else:
                parameter = PARAMETER

        for k, v in parameter.items():
            setattr(self, k, v)

        if abs(self.OV_H - 2) < 0.1:  # set to nearby integers as they are faster
            self.OV_H = 2
        if abs(self.OV_H - 1) < 0.1:
            self.OV_H = 1

        self.progress_callback = progress_callback
        self.extended_mode = extended_mode
        self.show_progress = show_progress
        z_axis = -np.array([0, 0, 1], dtype=np.float64)
        orientations = [[z_axis, 0.0]]

        # Preprocess the input mesh format.
        t_start = time()
        self._progress = 0  # progress in percent of tweaking
        self.update_progress(self._progress + 18)
        # Load mesh from file into class variable
        self.mesh = self.preprocess(content)

        # if a favoured side is specified, load it to weight
        if favside:
            self.favour_side(favside)
        t_pre = time()
        self.update_progress(self._progress + 18)
        # Searching promising orientations:
        orientations += self.area_cumulation(10)
        # 拿到面积最大的10个方向
        # orientations的形状类似:
        # [[[1, 2, 3], 4],
        #  [[2, 3, 4], 5],
        #  [[3, 4, 5], 6],
        #  [[4, 5, 6], 7]]
        # 前三个数字一组是面片法向量
        # 最后一个是面片面积大小

        t_areacum = time()
        self.update_progress(self._progress + 18)
        if extended_mode:
            # 如果是拓展模式
            orientations += self.death_star(12)
            orientations += self.add_supplements()
            orientations = self.remove_duplicates(orientations)

        if verbose:
            print("Examine {} orientations:".format(len(orientations)))
            print("  %-30s %-10s%-10s%-10s%-10s " %
                  ("Alignment:", "Bottom:", "Overhang:", "Contour:", "Unpr.:"))

        t_ds = time()
        self.update_progress(self._progress + 18)
        # Calculate the unprintability for each orientation found in the gathering algorithms
        results = np.empty((len(orientations), 7), dtype=np.float64)
        # np.empty(shape, dtype=float, order='c' or 'fortran')
        for side_idx, side in enumerate(orientations):
            # orientations里存了每个mesh的数据
            # 每次side拿出来的是一个mesh的数据
            # side[0]的数据就是该mesh的法向量
            orientation = -1 * np.array(side[0], dtype=np.float64)
            # orientation就是某个mesh的法向量的相反向量
            results[side_idx, 0] = orientation[0]
            results[side_idx, 1] = orientation[1]
            results[side_idx, 2] = orientation[2]
            # results[side_idx, :4]保存的就是mesh的法向量

            self.project_vertices(orientation)
            '''
            mesh.shape = (n, 6, 3)
            0: normals
            1, 2, 3: vertex
            4: (0, 1, 2)三个位置, 0号位置是mesh第0个顶点和orientation的内积, 1和2类推
            5: (面片面积, 4中三个点内积max, 4中三个点内积median)
            三个 点和向量的内积应该表现了 每个点点在该向量方向上,相对的位置,谁在前面谁在后面
            '''
            bottom, overhang, contour = self.calc_overhang(orientation, min_volume=min_volume)
            results[side_idx, 3] = bottom
            results[side_idx, 4] = overhang
            results[side_idx, 5] = contour

            unprintability = self.target_function(bottom, overhang, contour, min_volume=min_volume)
            results[side_idx, 6] = unprintability
        self.update_progress(self._progress + 18)

        # Remove the mesh structure as soon as it is not used anymore
        del self.mesh

        # evaluate the best alignments and calculate the rotation parameters
        results = results[results[:, -1].argsort()]  # [:5]]  # previously, the best 5 alignments were stored
        if verbose:
            for idx in range(results.shape[0]):
                print("  %-10.4f%-10.4f%-10.4f  %-10.2f%-10.2f%-10.2f%-10.4f "
                      % (tuple(results[idx])))
        t_lit = time()

        if verbose:
            print("""Time-stats of algorithm:
    Preprocessing:    \t{pre:2f} s
    Area Cumulation:  \t{ac:2f} s
    Death Star:       \t{ds:2f} s
    Lithography Time:  \t{lt:2f} s
    Total Time:        \t{tot:2f} s""".format(
                pre=t_pre - t_start, ac=t_areacum - t_pre, ds=t_ds - t_areacum,
                lt=t_lit - t_ds, tot=t_lit - t_start))

        # The list best_5_results is of the form:
        # [[orientation0, bottom_area0, overhang_area0, contour_line_length, unprintability (gives the order),
        #       [euler_vector, euler_angle (in rad), rotation matrix]],
        #   orientation1, ..
        if len(results) > 0:
            self.alignment = results[0][:3]
            self.rotation_axis, self.rotation_angle, self.matrix = self.euler(results[0][0:3])
            self.euler_parameter = [self.rotation_axis, self.rotation_angle]
            self.bottom_area = results[0][3]
            self.overhang_area = results[0][4]
            self.contour = results[0][5]
            self.unprintability = results[0][6]
            self.all_orientations = results
            self.best_5 = results[:5]
            self.time = t_lit - t_start

        # Finish with a nice clean newline, as print_progress rewrites updates without advancing below.
        if show_progress:
            print("\n")

    def target_function(self, bottom, overhang, contour, min_volume):
        """This function returns the Unprintability for a given set of bottom
        overhang area and bottom contour length, based on an ordinal scale.
        Args:
            bottom (float): bottom area size.
            overhang (float): overhanging area size.
            contour (float): length of the bottom's contour.
            min_volume (bool): Minimise volume of support material or supported surface area
        Returns:
            a value for the unprintability. The smaller, the better."""
        if min_volume:  # minimize the volume of support material
            overhang /= 25  # a volume is of higher dimension, so the overhang have to be reduced
            return (self.TAR_A * (overhang + self.TAR_B) + self.RELATIVE_F * (overhang + self.TAR_C) /
                         (self.TAR_D + self.CONTOUR_F * contour + self.BOTTOM_F * bottom + self.TAR_E * overhang))
        else:
            return (self.TAR_A * (overhang + self.TAR_B) + self.RELATIVE_F *
                    (overhang + self.TAR_C) / (self.TAR_D + self.CONTOUR_F * contour + self.BOTTOM_F * bottom))

    def preprocess(self, content):
        """The Mesh format gets preprocessed for a better performance and stored into self.mesh
        Args:
            content (np.array): undefined representation of the mesh
        Returns:
            mesh (np.array): with format face_count x 6 x 3.
        """
        # mesh是一个纯粹的点集[[], [], [], []]
        mesh = np.array(content, dtype=np.float64)

        # prefix area vector, if not already done (e.g. in STL format)
        if mesh.shape[1] == 3:
            # 检查每个点的坐标信息是不是三个,可能少了某一个轴的坐标信息
            row_number = int(len(content) / 3)
            # 总点数除三得到面片数
            mesh = mesh.reshape(row_number, 3, 3)

            # v0是所有面片的第一个坐标点,v0是一个列表,记录了各个面片的第一个坐标点
            v0 = mesh[:, 0, :]
            v1 = mesh[:, 1, :]
            v2 = mesh[:, 2, :]

            # 得到所有面片的法线
            normals = np.cross(np.subtract(v1, v0), np.subtract(v2, v0)) \
                .reshape(row_number, 1, 3)
            # 按列顺序将元素堆叠,mesh.shape = (mesh_num, 3, 3) 加上每个面片的法向量变成 (mesh_num, 4, 3)
            mesh = np.hstack((normals, mesh))

        # saves the amount of facets
        face_count = mesh.shape[0]

        # append columns with a_min, area_size
        addendum = np.zeros((face_count, 2, 3))
        # addendum.shape = [[[1, 2, 3],
        #                    [2, 3, 4]],
        #                    ......
        #                    ......
        #                   [[n, b, m],
        #                    [n, m, b]]]
        # 上面堆叠以后,mesh[:, 0, 2]是该mesh的法线
        # 获得每个mesh的每个顶点坐标的z轴
        addendum[:, 0, 0] = mesh[:, 1, 2]
        addendum[:, 0, 1] = mesh[:, 2, 2]
        addendum[:, 0, 2] = mesh[:, 3, 2]

        # calc area size
        # mesh[:, 0, :] 每个mesh的法向量
        # 下面得到面片的面积大小(是个平行四边形还要除2)
        addendum[:, 1, 0] = np.sqrt(np.sum(np.square(mesh[:, 0, :]), axis=-1)).reshape(face_count)
        # 1:4其实就是从序号一到4之前,其实最后一个序号是3,这里和1:一样
        addendum[:, 1, 1] = np.max(mesh[:, 1:4, 2], axis=1)
        addendum[:, 1, 2] = np.median(mesh[:, 1:4, 2], axis=1)
        mesh = np.hstack((mesh, addendum))
        # mesh.shape = (n, 6, 3)
        # 0: normals
        # 1,2,3: vertex
        # 4: z value
        # 5: (面片面积, max, median)

        # filter faces without area
        mesh = mesh[mesh[:, 5, 0] != 0]
        # 取出 面片面积 不等于 0 的所有面的信息.
        face_count = mesh.shape[0]

        # normalise area vector and correct area size
        mesh[:, 0, :] = mesh[:, 0, :] / mesh[:, 5, 0].reshape(face_count, 1)
        mesh[:, 5, 0] = mesh[:, 5, 0] / 2  # halve, because areas are triangles and not parallelograms

        # remove small facets (these are essential for contour calculation)
        # NEGL_FACE_SIZE 忽略面大小 是一个外部传入的参数,忽略该面面积的临界值
        if self.NEGL_FACE_SIZE > 0:
            negl_size = [0.1 * x if self.extended_mode else x for x in [self.NEGL_FACE_SIZE]][0]
            filtered_mesh = mesh[np.where(mesh[:, 5, 0] > negl_size)]
            if len(filtered_mesh) > 100:
                # 这里不知道为啥要>100
                mesh = filtered_mesh

        sleep(0)  # Yield, so other threads get a bit of breathing space.
        return mesh
        # mesh.shape = (n, 5, 3)

    def favour_side(self, favside):
        """This function weights the size of orientations closer than 45 deg
        to a favoured side higher.
        Args:
            favside (string): the favoured side  "[[0,-1,2.5],3]"
        Returns:
            a weighted mesh or the original mesh in case of invalid input
        """
        if isinstance(favside, str):
            try:
                restring = r"(-?\d*\.{0,1}\d+)[, []]*(-?\d*\.{0,1}\d+)[, []]*(-?\d*\.{0,1}\d+)\D*(-?\d*\.{0,1}\d+)"
                # restring中有四个括号
                # group(0)表示四个括号都匹配,返回整体匹配结果
                # group(1)表示返回第一个括号的匹配结果
                x = float(re.search(restring, favside).group(1))
                y = float(re.search(restring, favside).group(2))
                z = float(re.search(restring, favside).group(3))
                f = float(re.search(restring, favside).group(4))
            except AttributeError:
                raise AttributeError("Could not parse input: favored side")
        else:
            raise AttributeError("Could not parse input: favored side")
        # 不然两个都引发错误

        # 数据归一化
        # 把favourside方向归一化
        norm = np.sqrt(np.sum(np.array([x, y, z], dtype=np.float64) ** 2))
        side = np.array([x, y, z], dtype=np.float64) / norm

        print("You favour the side {} with a factor of {}".format(side, f))

        # Filter the aligning orientations
        # 用每个mesh的法向量和favour面的法向量作差
        diff = np.subtract(self.mesh[:, 0, :], side)
        # 相差不能大于某个参数


        align = np.sum(diff * diff, axis=1) < 0.7654  # former ANGLE_SCALE, set static to 43.85°
        # 通过align得到一个bool列表,记录的是该位置上的mesh是否与favourside对齐,再通过下面这行代码,对上面的结果取反,true变false
        # 得到不对齐的面片
        mesh_not_align = self.mesh[np.logical_not(align)]
        # 得到对齐的面片
        mesh_align = self.mesh[align]

        # 将面片面积数据乘上系数
        mesh_align[:, 5, 0] = f * mesh_align[:, 5, 0]  # weight aligning orientations

        self.mesh = np.concatenate((mesh_not_align, mesh_align), axis=0)

    def area_cumulation(self, best_n):
        """
        Gathering promising alignments by the accumulation of
        the magnitude of parallel area vectors.
        Args:
            best_n (int): amount of orientations to return.
        Returns:
            list of the common orientation-tuples.
        """
        orient = Counter()
        # len(self.mesh)就是有效的面片数
        for index in range(len(self.mesh)):  # Accumulate area-vectors
            # self.mesh[index, 5, 0]指的是index号面片的面积
            # self.mesh[index, 0] 是某个面的法向量
            # orient直接拿该法向量作为字典的键,而值是面积,所以orient字典存储{面: 面积}的键值对
            # 下面是将所有朝向该面的mesh的面积全部累加起来
            # 作为这个面的面积
            orient[tuple(self.mesh[index, 0] + 0.0)] += self.mesh[index, 5, 0]

        top_n = orient.most_common(best_n)
        # 返回最大的键
        sleep(0)  # Yield, so other threads get a bit of breathing space.
        return top_n

    def death_star(self, best_n):
        """
        Creating random faces by adding a random vertex to an existing edge.
        Common orientations of these faces are promising orientations for
        placement.
        Args:
            best_n (int): amount of orientations to return.
        Returns:
            list of the common orientation-tuples.
        """
        # 他的意思是应该是,不通过遍历面,而是通过随机抽取一条边与三个点来添加面,将这些面作为可能的方向

        # Small files need more calculations
        mesh_len = len(self.mesh)
        # 计算目标的ceiling值,ceiling是向上取整,floor是向下取整
        # 这里为什么是这么计算的iterations不清楚
        iterations = int(np.ceil(20000 / (mesh_len + 100)))

        # 拿出mesh数据中的三个顶点数据
        vertexes = self.mesh[:mesh_len, 1:4, :]
        tot_normalized_orientations = np.zeros((iterations * mesh_len + 1, 3))
        for i in range(iterations):
            # np.random.choice(a, size, replace=None, p=None)
            # 若a是数组,则从a中选出size个
            # 若a是int,则从0到a-1随机采样size个
            two_vertexes = vertexes[:, np.random.choice(3, 2, replace=False)]
            vertex_0 = two_vertexes[:, 0, :]
            vertex_1 = two_vertexes[:, 1, :]
            # 前两个顶点都是随机在同一个mesh中选出来的点

            # Using a linear congruency generator instead to choice pseudo
            # random vertexes. Adding i to get more iterations.
            # 最后这个点直接就是随机的mesh
            vertex_2 = vertexes[(np.arange(mesh_len) * 127 + 8191 + i) % mesh_len, i % 3, :]
            normals = np.cross(np.subtract(vertex_2, vertex_0),
                               np.subtract(vertex_1, vertex_0))
            # 得到这片随机面片的法向量

            # normalise area vector
            lengths = np.sqrt((normals * normals).sum(axis=1)).reshape(mesh_len, 1)
            # ignore ZeroDivisions
            with np.errstate(divide='ignore', invalid='ignore'):
                # 一个上下文管理器,让接下来的行为忽略某些错误
                # np.around是近似 np.true_divide是除法
                normalized_orientations = np.around(np.true_divide(normals, lengths),
                                                    decimals=6)

            # 将这个数据添加入tot_normalized_orientations
            # 可能是一个(n, 3)的shape
            tot_normalized_orientations[mesh_len * i: mesh_len * (i + 1)] = normalized_orientations
            # 得到本次迭代下的所有方向
            sleep(0)  # Yield, so other threads get a bit of breathing space.

        # search the most common orientations
        # np.inner 两数组内积
        # 这下面的计算看不懂为什么要这么计算
        orientations = np.inner(np.array([1, 1e3, 1e6]), tot_normalized_orientations)
        orient = Counter(orientations)
        top_n = orient.most_common(best_n)
        # 最后过滤了一些项
        # {sum_side: count} sum_side: 内积和 count: 出现次数
        # 下面的筛选条件就是出现次数>2
        top_n = list(filter(lambda x: x[1] > 2, top_n))

        candidate = list()
        for sum_side, count in top_n:
            # tot_normalized_orientations[orientations == sum_side]返回满足条件的面的法向量,用unique将重复法向量去掉,
            # 留下一个,并且将这一个出现的次数返回
            # 即face_unique和face_count
            # np.unique 去除重复元素,并且按照元素由小到大返回,还要返回每个元素出现的次数
            face_unique, face_count = np.unique(tot_normalized_orientations[orientations == sum_side], axis=0,
                                                return_counts=True)
            # 这里的加只是在list里增加了项
            candidate += [[list(face_unique[i]), count] for i, count in enumerate(face_count)]
        # Filter non-injective singles
        # x[1]>2 即某个index下上面对应的count>2
        candidate = list(filter(lambda x: x[1] >= 2, candidate))
        # also add anti-parallel orientations
        # 还要把一切的反方向向量加进去不知道为了啥
        candidate += [[list((-v[0][0], -v[0][1], -v[0][2])), v[1]] for v in candidate]
        return candidate

    @staticmethod
    def add_supplements():
        """Supplement 18 additional vectors.
        Returns:
            Basic Orientation Field"""
        v = [[0, 0, -1], [0.70710678, 0, -0.70710678], [0, 0.70710678, -0.70710678],
             [-0.70710678, 0, -0.70710678], [0, -0.70710678, -0.70710678],
             [1, 0, 0], [0.70710678, 0.70710678, 0], [0, 1, 0], [-0.70710678, 0.70710678, 0],
             [-1, 0, 0], [-0.70710678, -0.70710678, 0], [0, -1, 0], [0.70710678, -0.70710678, 0],
             [0.70710678, 0, 0.70710678], [0, 0.70710678, 0.70710678],
             [-0.70710678, 0, 0.70710678], [0, -0.70710678, 0.70710678], [0, 0, 1]]
        v = [[list([float(j) for j in i]), 0] for i in v]
        return v

    @staticmethod
    def remove_duplicates(old_orients):
        """
        Removing duplicate and similar orientations.
        Args:
            old_orients (list): list of faces
        Returns:
            Unique orientations"""
        alpha = 5  # in degrees
        tol_dist = alpha * np.pi / 180  # nearly same as with sin
        orientations = list()
        for i in old_orients:
            duplicate = None
            for j in orientations:
                # redundant vectors have an difference smaller than
                # dist = ||y-x|| < tol_dist-> alpha = 5 degrees
                if (i[0][0] - j[0][0]) ** 2 + (i[0][1] - j[0][1]) ** 2 + (i[0][2] - j[0][2]) ** 2 < tol_dist ** 2:
                    duplicate = True
                    break
            # 检查所有old_orientations中的向量,满足条件的才加入新的orientation
            if duplicate is None:
                orientations.append(i)
        return orientations

    def project_vertices(self, orientation):
        """Supplement the mesh array with scalars (max and median)
        for each face projected onto the orientation vector.
        Args:
            orientation (np.array): with format 3 x 3.
        Returns:
            adjusted mesh.
        """
        # 在这个函数里改动的都是mesh,orientation没有发生变化
        # mesh点1和方向向量的内积
        self.mesh[:, 4, 0] = np.inner(self.mesh[:, 1, :], orientation)
        # mesh点2和方向向量的内积
        self.mesh[:, 4, 1] = np.inner(self.mesh[:, 2, :], orientation)
        # mesh点3和方向向量的内积
        self.mesh[:, 4, 2] = np.inner(self.mesh[:, 3, :], orientation)
        # (0, 1, 2)三个位置, 0号位置是mesh第0个顶点和orientation的内积,1和2类推

        self.mesh[:, 5, 1] = np.max(self.mesh[:, 4, :], axis=1)
        # 现在该位置变成了上面算出来的最大的内积
        self.mesh[:, 5, 2] = np.median(self.mesh[:, 4, :], axis=1)
        # 现在该位置变成了上面算出来的内积的中位数
        sleep(0)  # Yield, so other threads get a bit of breathing space.

    def calc_overhang(self, orientation, min_volume):
        """Calculating bottom and overhang area for a mesh regarding the vector n.
        Args:
            orientation (np.array): with format 3 x 3.
            min_volume (bool): minimize the support material volume or supported surfaces
        Returns:
            the total bottom size, overhang size and contour length of the mesh
        """
        total_min = np.amin(self.mesh[:, 4, :])
        # np.amin是按轴找出该轴上的最小值,就是mesh三个顶点和orientation的内积的最小值,全局最小
        # axis = 0 的话total_min.shape = (1, 3)

        # filter bottom area
        # 将满足后面条件的面片全取出来,然后将这些面片的面积全部加起来
        # 前面有个函数将法向量与favour面片法向量有一定偏差的面片的面积做过了处理,估计是将该面片投影在favour面方向上
        # 由此得到一个比较科学的bottom大小
        bottom = np.sum(self.mesh[np.where(self.mesh[:, 5, 1] < total_min + self.FIRST_LAY_H), 5, 0])
        # # equal than:
        # bottoms = mesh[np.where(mesh[:, 5, 1] < total_min + FIRST_LAY_H)]
        # if len(bottoms) > 0: bottom = np.sum(bottoms[:, 5, 0])
        # else: bottom = 0

        # filter overhangs
        # 用内积可以轻松表示一些关系,向量内积小说明夹角大,内极大说明夹角小,如果内积大于0,说明在同方向,内积<0说明反方向
        # 下面要求内积小于一定值说明要求两个向量夹角大,夹角大了才有悬挑overhang
        # 这里希望
        overhangs = self.mesh[np.where(np.inner(self.mesh[:, 0, :], orientation) < self.ASCENT)]
        overhangs = overhangs[np.where(overhangs[:, 5, 1] > (total_min + self.FIRST_LAY_H))]
        # 上面这个条件选择不是很懂是什么意思

        if self.extended_mode:
            # 看这些选出来的悬挑的面片的法向量是不是刚好和要求的方向相反,因为与要求方向相反才是悬挑
            # all 是在某个轴的方向上计算逻辑与(and)
            # 然后把相反的,符合条件的悬挑的面积加起来
            plafond = np.sum(overhangs[(overhangs[:, 0, :] == -orientation).all(axis=1), 5, 0])
        else:
            plafond = 0

        if len(overhangs) > 0:
            # 这里应该是最小支撑体积?
            if min_volume:
                # 通过mean求平均应该是为了得到三角形的中点
                heights = np.inner(overhangs[:, 1:4, :].mean(axis=1), orientation) - total_min

                inner = np.inner(overhangs[:, 0, :], orientation) - self.ASCENT
                # overhang = np.sum(heights * overhangs[:, 5, 0] * np.abs(inner * (inner < 0)) ** 2)
                overhang = np.sum((self.height_offset + self.height_log * np.log(self.height_log_k * heights + 1)) *
                                  overhangs[:, 5, 0] * np.abs(inner * (inner < 0)) ** self.OV_H)
            else:
                # overhang = np.sum(overhangs[:, 5, 0] * 2 *
                #                   (np.amax((np.zeros(len(overhangs)) + 0.5,
                #                             - np.inner(overhangs[:, 0, :], orientation)),
                #                            axis=0) - 0.5) ** 2)
                # improved performance by finding maximum using the multiplication method, see:
                # https://stackoverflow.com/questions/32109319/how-to-implement-the-relu-function-in-numpy
                inner = np.inner(overhangs[:, 0, :], orientation) - self.ASCENT
                overhang = 2 * np.sum(overhangs[:, 5, 0] * np.abs(inner * (inner < 0)) ** 2)
            overhang -= self.PLAFOND_ADV * plafond

        else:
            overhang = 0

        # filter the total length of the bottom area's contour
        if self.extended_mode:
            # contours = self.mesh[total_min+self.FIRST_LAY_H < self.mesh[:, 5, 1]]
            contours = self.mesh[np.where(self.mesh[:, 5, 2] < total_min + self.FIRST_LAY_H)]

            if len(contours) > 0:
                conlen = np.arange(len(contours))
                sortsc0 = np.argsort(contours[:, 4, :], axis=1)[:, 0]
                # 将contours中的所有的记录每个点与方向内积的三个元素从小到大排序,
                # 然后挑出每个mesh中的排0的点的原始序号(排序前有012,现在就是获得排序前的索引)
                sortsc1 = np.argsort(contours[:, 4, :], axis=1)[:, 1]
                # 然后挑出每个mesh中的排1的点的原始序号(排序前有012,现在就是获得排序前的索引)

                # 下面这个conlen按顺序记录了从0到n的数字,这么写就避开使用循环
                # 这里sortsc0为什么要＋1
                # contours[:, 4, :]记录了1,2,3行三个顶点和方向的内积,sortsc0+1刚好得到内积最小的顶点的行数
                # 两行坐标相减作差
                con = np.array([np.subtract(
                    contours[conlen, 1 + sortsc0, :],
                    contours[conlen, 1 + sortsc1, :])])

                contours = np.sum(np.power(con, 2), axis=-1) ** 0.5
                contour = np.sum(contours) + self.CONTOUR_AMOUNT * len(contours)
            else:
                contour = 0
        else:  # consider the bottom area as square, bottom=a**2 ^ contour=4*a
            contour = 4 * np.sqrt(bottom)

        sleep(0)  # Yield, so other threads get a bit of breathing space.
        return bottom, overhang, contour

    def update_progress(self, new_progress):
        self._progress = new_progress
        if self.show_progress:
            os.system('cls')
            print("Progress is: {progress} ".format(progress=new_progress))
        if self.progress_callback:
            self.progress_callback(new_progress)

    def euler(self, bestside):
        """Calculating euler rotation parameters and rotational matrix.
        Args:
            bestside (np.array): vector of the best orientation (3).
        Returns:
            rotation axis, rotation angle, rotational matrix.
        """
        if not isinstance(bestside, (list, np.ndarray)) or len(bestside) != 3:
            print(f"Best side not as excepted: {bestside}, type: {type(bestside)}")
        if bestside[0] ** 2 + bestside[1] ** 2 + (bestside[2] + 1.) ** 2 < abs(self.VECTOR_TOL):
            rotation_axis = [1., 0., 0.]
            phi = np.pi
        elif bestside[0] ** 2 + bestside[1] ** 2 + (bestside[2] - 1.) ** 2 < abs(self.VECTOR_TOL):
            rotation_axis = [1., 0., 0.]
            phi = 0.
        else:
            phi = np.pi - np.arccos(-bestside[2] + 0.0)
            rotation_axis = np.array(
                [-bestside[1] + 0.0, bestside[0] + 0.0, 0.])  # the z-axis is fixed to 0 for this rotation
            rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)  # normalization

        v = rotation_axis
        cos_phi = np.cos(phi)
        sin_phi = np.sin(phi)
        rotational_matrix = np.empty((3, 3), dtype=np.float64)
        rotational_matrix[0, 0] = v[0] * v[0] * (1 - cos_phi) + cos_phi
        rotational_matrix[0, 1] = v[0] * v[1] * (1 - cos_phi) - v[2] * sin_phi
        rotational_matrix[0, 2] = v[0] * v[2] * (1 - cos_phi) + v[1] * sin_phi
        rotational_matrix[1, 0] = v[1] * v[0] * (1 - cos_phi) + v[2] * sin_phi
        rotational_matrix[1, 1] = v[1] * v[1] * (1 - cos_phi) + cos_phi
        rotational_matrix[1, 2] = v[1] * v[2] * (1 - cos_phi) - v[0] * sin_phi
        rotational_matrix[2, 0] = v[2] * v[0] * (1 - cos_phi) - v[1] * sin_phi
        rotational_matrix[2, 1] = v[2] * v[1] * (1 - cos_phi) + v[0] * sin_phi
        rotational_matrix[2, 2] = v[2] * v[2] * (1 - cos_phi) + cos_phi

        return [list(rotation_axis), phi, rotational_matrix]

    def __str__(self):
        response = "Result-stats:"
        response += "\n  Tweaked Z-axis: \t{}".format(self.alignment)
        response += "\n  Rotation Axis: {}, angle: {}".format(self.rotation_axis, self.rotation_angle)
        response += """\n  Rotation matrix: 
    {:2f}\t{:2f}\t{:2f}
    {:2f}\t{:2f}\t{:2f}
    {:2f}\t{:2f}\t{:2f}""".format(self.matrix[0][0], self.matrix[0][1], self.matrix[0][2],
                                  self.matrix[1][0], self.matrix[1][1], self.matrix[1][2],
                                  self.matrix[2][0], self.matrix[2][1], self.matrix[2][2])
        response += "\n  Printability: \t{}".format(self.printability)
        return response
