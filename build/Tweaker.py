#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
import os
from time import time
import struct
import traceback
import numpy as np
from MeshTweaker import Tweak

# if __name__ == '__main__':
    # from MeshTweaker import Tweak
    # import FileHandler
# else:
#     from .MeshTweaker import Tweak
#     from . import FileHandler

# You can preset the default model in line 42

__author__ = "Christoph Schranz, Salzburg Research"
__version__ = "3.9, October 2020"


import os
import zipfile
import xml.etree.ElementTree as ET

namespace = {
    "3mf": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02",
    "m"  : "http://schemas.microsoft.com/3dmanufacturing/material/2015/02"
}


def Read3mf(f):
    '''load parts of the 3mf with their properties'''
    # The base object of 3mf is a zipped archive.
    archive = zipfile.ZipFile(f, "r")
    try:
        root = ET.parse(archive.open("3D/3dmodel.model"))

        # There can be multiple objects, try to load all of them.
        objects = root.findall("./3mf:resources/3mf:object", namespace)
        if len(objects) == 0:
            print("No objects found in 3MF file %s, either the file is damaged or you are using an outdated format", f)
            return None

        obj_meshs = list()
        c = 0
        for obj in objects:
            if obj.findall(".//3mf:mesh", namespace) == []:
                continue
            obj_meshs.append(dict())

            objectid = obj.get("id")
            obj_meshs[c]["objectid"] = objectid

            vertex_list = []
            obj_meshs[c]["mesh"] = list()
            # for vertex in object.mesh.vertices.vertex:
            for vertex in obj.findall(".//3mf:vertex", namespace):
                vertex_list.append([vertex.get("x"), vertex.get("y"), vertex.get("z")])

            triangles = obj.findall(".//3mf:triangle", namespace)
            # for triangle in object.mesh.triangles.triangle:
            for triangle in triangles:
                v1 = int(triangle.get("v1"))
                v2 = int(triangle.get("v2"))
                v3 = int(triangle.get("v3"))
                obj_meshs[c]["mesh"].append([float(vertex_list[v1][0]), float(vertex_list[v1][1]), float(vertex_list[v1][2])])
                obj_meshs[c]["mesh"].append([float(vertex_list[v2][0]), float(vertex_list[v2][1]), float(vertex_list[v2][2])])
                obj_meshs[c]["mesh"].append([float(vertex_list[v3][0]), float(vertex_list[v3][1]), float(vertex_list[v3][2])])

            try:
                obj_meshs[c]["Transform"] = getTransformation(root, objectid)
            except:
                pass

            ##            try:
            ##                color_list = list()
            ##                colors = root.findall('.//m:color', namespace)
            ##                if colors:
            ##                    for color in colors:
            ##                        color_list.append(color.get("color",0))
            ##                    obj_meshs[c]["color"] = color_list
            ##            except AttributeError:
            ##                pass # Empty list was found. Getting transformation is not possible

            c = c + 1


    except Exception as e:
        print("exception occured in 3mf reader: %s" % e)
        return None
    return obj_meshs


def getTransformation(root, objectid):
    builds = root.findall(".//3mf:item", namespace)
    transforms = list()
    for item in builds:
        if item.get("transform"):
            transforms.append((item.get("objectid"), item.get("transform")))
    components = root.findall(".//3mf:components", namespace)
    objects = root.findall("./3mf:resources/3mf:object", namespace)
    for (transid, transform) in transforms:
        for obj in objects:
            if transid == obj.get("id"):
                obj_ids = obj.findall(".//3mf:component", namespace)
                for obj_id in obj_ids:
                    if obj_id.get("objectid") == objectid:
                        # print(transform)
                        break
    return transform


def rotate3MF(f, outfile, objs):
    # TODO doesn't work at the moment
    archive = zipfile.ZipFile(f, "r")
    root = ET.parse(archive.open("3D/3dmodel.model"))

    for obj in objs:
        itemid = None
        # get build id for transform value
        objects3MF = root.findall("./3mf:resources/3mf:object", namespace)
        for elem in objects3MF:
            for component in elem.findall(".//3mf:component", namespace):
                if component.get("objectid") == obj["objectid"]:
                    # print("objid", elem.get("id"))
                    itemid = elem.get("id")

        if itemid:
            for item in root.findall(".//3mf:build/3mf:item", namespace):
                if item.get("objectid") == itemid:
                    item.set("transform", obj["transform"])
        else:
            pass

    # Writing the changed model in the output file
    indir = os.path.splitext(f)[0]
    zipf = zipfile.ZipFile(outfile, 'w', zipfile.ZIP_DEFLATED)
    zipdir(indir, zipf)
    zipf.close()


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))


class FileHandler:
    def __init__(self):
        pass

    def load_mesh(self, inputfile):
        """This module loads the content of a 3D file as mesh array."""

        filetype = os.path.splitext(inputfile)[1].lower()
        if filetype == ".stl":
            f = open(inputfile, "rb")
            if not f.readable():
                raise Exception("File is not readable.")
            try:
                if "solid" in str(f.read(5).lower()):
                    try:
                        f = open(inputfile, "r")
                        objs = self.load_ascii_stl(f)
                    except UnicodeDecodeError:
                        # There are cases of binary STL with prefix 'solid', reopen file
                        f = open(inputfile, "rb")
                        f.seek(5, os.SEEK_SET)
                        objs = self.load_binary_stl(f)
                else:
                    objs = self.load_binary_stl(f)
            except Exception as ex:
                # Get current system exception
                ex_type, ex_value, ex_traceback = sys.exc_info()
                # Extract unformatter stack traces as tuples
                trace_back = traceback.extract_tb(ex_traceback)
                # Format stacktrace
                stack_trace = list()
                for trace in trace_back:
                    stack_trace.append("File : %s , Line : %d, Func.Name : %s, Message : %s" % (
                        trace[0], trace[1], trace[2], trace[3]))

                print("""Exception of type '{}' in reading the file:\n'{}'
Stack trace: '{}' 
The file may be corrupt, please check if the file can be opened with ofter software. 
If it is readable by other software, you can help to improve this software by 
opening a github issue and attaching the file.
Best,\nyour Auto-Rotate Developer\n""".format(ex_type.__name__, str(ex), stack_trace))
                raise Exception("File is not readable.")

        elif filetype == ".3mf":
            object = Read3mf(inputfile)  # TODO not implemented
            # objs[0] = {"mesh": list(), "name": "binary file"}
            objs = {0: {"mesh": object[0]["mesh"], "name": "3mf file"}}
        elif filetype == ".obj":
            f = open(inputfile, "rb")
            objs = self.load_obj(f)

        else:
            raise Exception("File type is not supported.")

        return objs

    @staticmethod
    def load_obj(f):
        """Load the content of an OBJ file."""
        objects = dict()
        vertices = list()
        objects[0] = {"mesh": list(), "name": "obj file"}
        for line in f:
            if "v" in line:
                data = line.split()[1:]
                vertices.append([float(data[0]), float(data[1]), float(data[2])])
        f.seek(0, 0)
        for line in f:
            if "f" in line:
                data = line.split()[1:]
                objects[0]["mesh"].append(vertices[int(data[0]) - 1])
                objects[0]["mesh"].append(vertices[int(data[1]) - 1])
                objects[0]["mesh"].append(vertices[int(data[2]) - 1])

        return objects

    @staticmethod
    def load_ascii_stl(f):
        """Load the content of an ASCII STL file."""
        objects = dict()
        part = 0
        objects[part] = {"mesh": list()}
        for line in f:
            if "vertex" in line:
                data = line.split()[1:]
                objects[part]["mesh"].append([float(data[0]), float(data[1]), float(data[2])])
            if "endsolid" in line:
                objects[part]["name"] = line.split()[-1]
                part += 1
                objects[part] = {"mesh": list()}

        # Delete empty parts:
        objs = dict()
        for k, v in objects.items():
            # k 取得part序号
            # v 取得字典存储的信息
            if len(v["mesh"]) > 3:
                # mesh中存储了点的坐标, 至少一个面片需要至少3个点,没有则是不成面
                objs[k] = v
        return objs

    @staticmethod
    def load_binary_stl(f):
        """Load the content of a binary STL file."""
        # Skip the header
        f.read(80 - 5)
        face_count = struct.unpack('<I', f.read(4))[0]
        objects = dict()
        objects[0] = {"mesh": list(), "name": "binary file"}
        for idx in range(0, face_count):
            data = struct.unpack("<ffffffffffffH", f.read(50))
            objects[0]["mesh"].append([data[3], data[4], data[5]])
            objects[0]["mesh"].append([data[6], data[7], data[8]])
            objects[0]["mesh"].append([data[9], data[10], data[11]])
        return objects

    def write_mesh(self, objects, info, outputfile, output_type="binarystl"):
        # if output_type == "3mf":  # TODO not implemented yet
        #     # transformation = "{} {} {} {} {} {} {} {} {} 0 0 1".
        #     # format(x.matrix[0][0], x.matrix[0][1], x.matrix[0][2],
        #     # x.matrix[1][0], x.matrix[1][1], x.matrix[1][2], x.matrix[2][0], x.matrix[2][1], x.matrix[2][2])
        #     #     obj["transform"] = transformation
        #     #     FileHandler.rotate3MF(args.inputfile, args.outputfile, objs)
        #     raise TypeError('The 3mf output format is not implemented yet.')

        if output_type == "asciistl":
            # Create seperate files with rotated content. If an IDE supports multipart placement,
            # set outname = outputfile
            for part, content in objects.items():
                mesh = content["mesh"]
                filename = content["name"]

                mesh = self.rotate_ascii_stl(info[part]["matrix"], mesh, filename)
                if len(objects.keys()) == 1:
                    outname = outputfile
                else:
                    outname = ".".join(outputfile.split(".")[:-1]) + "_{}.stl".format(part)
                with open(outname, 'w') as outfile:
                    outfile.write(mesh)

        else:  # binary STL, binary stl can't support multiparts
            # Create seperate files with rotated content.
            header = "Tweaked on {}".format(time.strftime("%a %d %b %Y %H:%M:%S")
                                            ).encode().ljust(79, b" ") + b"\n"
            for part, content in objects.items():
                mesh = objects[part]["mesh"]
                partlength = int(len(mesh) / 3)
                mesh = self.rotate_bin_stl(info[part]["matrix"], mesh)

                if len(objects.keys()) == 1:
                    outname = outputfile
                else:
                    outname = ".".join(outputfile.split(".")[:-1]) + "_{}.stl".format(part)
                length = struct.pack("<I", partlength)
                with open(outname, 'wb') as outfile:
                    outfile.write(bytearray(header + length + b"".join(mesh)))

    @staticmethod
    def rotate_3mf(*arg):
        rotate3MF(*arg)

    def rotate_ascii_stl(self, rotation_matrix, content, filename):
        """Rotate the mesh array and save as ASCII STL."""
        mesh = np.array(content, dtype=np.float64)

        # prefix area vector, if not already done (e.g. in STL format)
        if len(mesh[0]) == 3:
            row_number = int(len(content) / 3)
            mesh = mesh.reshape(row_number, 3, 3)

        # upgrade numpy with: "pip install numpy --upgrade"
        mesh = np.matmul(mesh, rotation_matrix)

        v0 = mesh[:, 0, :]
        v1 = mesh[:, 1, :]
        v2 = mesh[:, 2, :]
        normals = np.cross(np.subtract(v1, v0), np.subtract(v2, v0)) \
            .reshape(int(len(mesh)), 1, 3)
        mesh = np.hstack((normals, mesh))

        tweaked = list("solid %s" % filename)
        tweaked += list(map(self.write_facett, list(mesh)))
        tweaked.append("\nendsolid %s\n" % filename)
        tweaked = "".join(tweaked)
        return tweaked

    @staticmethod
    def write_facett(facett):
        return """\nfacet normal %f %f %f
        outer loop
            vertex %f %f %f
            vertex %f %f %f
            vertex %f %f %f
        endloop
    endfacet""" % (facett[0, 0], facett[0, 1], facett[0, 2], facett[1, 0],
                   facett[1, 1], facett[1, 2], facett[2, 0], facett[2, 1],
                   facett[2, 2], facett[3, 0], facett[3, 1], facett[3, 2])

    def rotate_bin_stl(self, rotation_matrix, content):
        """Rotate the object and save as binary STL. This module is currently replaced
        by the ascii version. If you want to use binary STL, please do the
        following changes in Tweaker.py: Replace "rotatebinSTL" by "rotateSTL"
        and set in the write sequence the open outfile option from "w" to "wb".
        However, the ascii version is much faster in Python 3."""
        mesh = np.array(content, dtype=np.float64)

        # prefix area vector, if not already done (e.g. in STL format)
        if len(mesh[0]) == 3:
            row_number = int(len(content) / 3)
            mesh = mesh.reshape(row_number, 3, 3)

        # upgrade numpy with: "pip install numpy --upgrade"
        mesh = np.matmul(mesh, rotation_matrix)

        v0 = mesh[:, 0, :]
        v1 = mesh[:, 1, :]
        v2 = mesh[:, 2, :]
        normals = np.cross(np.subtract(v1, v0), np.subtract(v2, v0)
                           ).reshape(int(len(mesh)), 1, 3)
        mesh = np.hstack((normals, mesh))
        # header = "Tweaked on {}".format(time.strftime("%a %d %b %Y %H:%M:%S")
        #                                 ).encode().ljust(79, b" ") + b"\n"
        # header = struct.pack("<I", int(len(content) / 3))  # list("solid %s" % filename)

        mesh = list(map(self.write_bin_facett, mesh))

        # return header + b"".join(tweaked_array)
        # return b"".join(tweaked_array)
        return mesh

    @staticmethod
    def write_bin_facett(facett):
        tweaked = struct.pack("<fff", facett[0][0], facett[0][1], facett[0][2])
        tweaked += struct.pack("<fff", facett[1][0], facett[1][1], facett[1][2])
        tweaked += struct.pack("<fff", facett[2][0], facett[2][1], facett[2][2])
        tweaked += struct.pack("<fff", facett[3][0], facett[3][1], facett[3][2])
        tweaked += struct.pack("<H", 0)

        return tweaked



def getargs():
    parser = argparse.ArgumentParser(description="Orientation tool for better 3D prints")
    parser.add_argument('-i ', action="store",
                        dest="inputfile", help="select input file")
    parser.add_argument('-o ', action="store", dest="outputfile", type=str,
                        help="select output file. '_tweaked' is postfix by default")
    parser.add_argument('-vb ', '--verbose', action="store_true", dest="verbose",
                        help="increase output verbosity", default=False)
    parser.add_argument('-p ', '--progress', action="store_true", dest="show_progress",
                        help="show the progress of Tweaking", default=False)
    parser.add_argument('-c ', '--convert', action="store_true", dest="convert",
                        help="convert 3mf to stl without tweaking", default=False)
    parser.add_argument('-t ', '--outputtype', action="store", dest="output_type", default=False,
                        help='set output representation [default="binarystl", "asciistl", "3mf"]')
    parser.add_argument('-x ', '--extended', action="store_true", dest="extended_mode", default=False,
                        help="using more algorithms and examine more alignments")
    parser.add_argument('-v ', '--version', action="store_true", dest="version",
                        help="print version number and exit", default=False)
    parser.add_argument('-r ', '--result', action="store_true", dest="result",
                        help="show result of calculation and exit without creating output file",
                        default=False)
    parser.add_argument('-fs', '--favside', type=str, dest="favside",
                        help="favour one orientation with a vector and weighting, e.g.  '[[0.,-1.,2.],3.]'",
                        default=None)
    parser.add_argument('-min', '--minimize', action="store", dest="minimize", default="vol",
                        help="choose to minimise overhanging surface [sur] or volume default=[vol] of support material")
    arguments = parser.parse_args()

    if arguments.version:
        print("Tweaker 3.9, (November 2020, parameter are optimized by an evolutionary algorithm)")
        return None
    # print("filepath")
    # print(arguments.inputfile)
    if not arguments.inputfile:
        try:
            curpath = os.path.dirname(os.path.realpath(__file__))
            arguments.inputfile = curpath + os.sep + "demo_object.stl"
            # arguments.inputfile = curpath + os.sep + "death_star.stl"
            # arguments.inputfile = curpath + os.sep + "pyramid.3mf"
            # arguments.inputfile = curpath + os.sep + "3DBenchy2.stl"
            arguments.inputfile = curpath + os.sep + "all.stl"
        except FileNotFoundError:
            return None
    if arguments.minimize:
        if "sur" in arguments.minimize.lower():
            arguments.volume = False
        elif "vol" in arguments.minimize.lower():
            arguments.volume = True
        else:
            print("Can't understand input '-min {}', using 'vol'.".format(arguments.minimize))
            arguments.volume = True
    if arguments.output_type:
        # print(arguments.output_type)
        if "3mf" in arguments.output_type.lower():
            filetype = "3mf"
        elif "asci" in arguments.output_type.lower():
            filetype = "asciistl"
        else:
            filetype = "binarystl"
    else:
        if "3mf" in os.path.splitext(arguments.inputfile)[1]:
            filetype = "3mf"
        else:
            filetype = "binarystl"
    arguments.output_type = filetype
    # print("Tweaker, arguments.output_type", arguments.output_type)
    if arguments.outputfile:
        filetype = arguments.outputfile.split(".")[-1].lower()
        if filetype not in ["stl", "3mf", "obj"]:
            raise TypeError("Filetype not supported")
        arguments.outputfile = ".".join(arguments.outputfile.split(".")[:-1]) + "." + filetype
        if not arguments.output_type:
            arguments.output_type = filetype
    else:
        if arguments.convert:
            arguments.outputfile = os.path.splitext(arguments.inputfile)[0] + "_converted"
        else:
            arguments.outputfile = os.path.splitext(arguments.inputfile)[0] + "_tweaked"

        if arguments.output_type == "3mf":
            arguments.outputfile += ".3mf"  # TODO not supported yet
        else:
            arguments.outputfile += ".stl"

    argv = sys.argv[1:]
    if len(argv) == 0:
        print("""No additional arguments. Testing calculation with 
demo object in verbose mode. Use argument -h for help.
""")
        arguments.convert = False
        arguments.verbose = False  # True
        # arguments.show_progress = True
        arguments.extended_mode = True
        arguments.favside = None  # "[[0,-0.5,1],2.5]"
        # arguments.output_type = "asciistl"
        # arguments.volume = True

    return arguments


def cli():
    global FileHandler
    # Get the command line arguments. Run in IDE for demo tweaking.
    stime = time()
    try:
        args = getargs()
        if args is None:
            sys.exit()
    except:
        raise

    try:
        FileHandler = FileHandler.FileHandler()
        objs = FileHandler.load_mesh(args.inputfile)
        if objs is None:
            sys.exit()
    except(KeyboardInterrupt, SystemExit):
        raise SystemExit("Error, loading mesh from file failed!")

    # Start of tweaking.
    if args.verbose:
        print("Calculating the optimal orientation:\n  {}"
              .format(args.inputfile.split(os.sep)[-1]))

    c = 0
    info = dict()
    for part, content in objs.items():
        mesh = content["mesh"]
        info[part] = dict()
        if args.convert:
            info[part]["matrix"] = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        else:
            try:
                cstime = time()
                x = Tweak(mesh, args.extended_mode, args.verbose, args.show_progress, args.favside, args.volume)
                info[part]["matrix"] = x.matrix
                info[part]["tweaker_stats"] = x
            except (KeyboardInterrupt, SystemExit):
                raise SystemExit("\nError, tweaking process failed!")

            # List tweaking results
            if args.result or args.verbose:
                print("Result-stats:")
                print(" Tweaked Z-axis: \t{}".format(x.alignment))
                print(" Axis {}, \tangle: {}".format(x.rotation_axis, x.rotation_angle))
                print(""" Rotation matrix: 
            {:2f}\t{:2f}\t{:2f}
            {:2f}\t{:2f}\t{:2f}
            {:2f}\t{:2f}\t{:2f}""".format(x.matrix[0][0], x.matrix[0][1], x.matrix[0][2],
                                          x.matrix[1][0], x.matrix[1][1], x.matrix[1][2],
                                          x.matrix[2][0], x.matrix[2][1], x.matrix[2][2]))
                print(" Unprintability: \t{}".format(x.unprintability))

                print("Found result:    \t{:2f} s\n".format(time() - cstime))

    if not args.result:
        try:
            FileHandler.write_mesh(objs, info, args.outputfile, args.output_type)
        except FileNotFoundError:
            raise FileNotFoundError("Output File '{}' not found.".format(args.outputfile))

    # Success message
    if args.verbose:
        print("Tweaking took:  \t{:2f} s".format(time() - stime))
        print("Successfully Rotated!")

class ARGS:
    def __init__(self, kwargs):
        self.inputfile = kwargs["inputfile"]
        self.outputfile = kwargs["outputfile"]
        self.verbose = kwargs["verbose"]
        self.show_progress = kwargs["show_progress"]
        self.convert = kwargs["convert"]
        self.output_type = kwargs["output_type"]
        self.extended_mode = kwargs["extended_mode"]
        self.version = kwargs["version"]
        self.result = kwargs["result"]
        # self.result = None
        self.favside = kwargs["favside"]
        self.volume = kwargs["volume"]
        self.minimize = kwargs["minimize"]
        # self.outputfile = os.path.splitext(self.inputfile)[0] + "_tweaked" + ".stl"
        # print(self.outputfile)
        print("ARGS init !!!")

def run(args):
    
    # Get the command line arguments. Run in IDE for demo tweaking.
    # stime = time()
    # print(np.array([1, 2, 3]))
    # print("before filehandler")

    # global FileHandler
    # Get the command line arguments. Run in IDE for demo tweaking.
    stime = time()
    # try:
    #     args = getargs()
    #     if args is None:
    #         sys.exit()
    # except:
    #     raise
    # args.outputfile = os.path.splitext(args.inputfile)[0] + "_tweaked" + ".stl"
    try:
        Handler = FileHandler()
        objs = Handler.load_mesh(args.inputfile)
        if objs is None:
            sys.exit()
    except(KeyboardInterrupt, SystemExit):
        raise SystemExit("Error, loading mesh from file failed!")

    # Start of tweaking.
    if args.verbose:
        print("Calculating the optimal orientation:\n  {}"
              .format(args.inputfile.split(os.sep)[-1]))

    c = 0
    info = dict()
    for part, content in objs.items():
        mesh = content["mesh"]
        info[part] = dict()
        if args.convert:
            info[part]["matrix"] = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        else:
            try:
                cstime = time()
                x = Tweak(mesh, args.extended_mode, args.verbose, args.show_progress, args.favside, args.volume)
                info[part]["matrix"] = x.matrix
                info[part]["tweaker_stats"] = x
            except (KeyboardInterrupt, SystemExit):
                raise SystemExit("\nError, tweaking process failed!")

            # List tweaking results
            if args.result or args.verbose:
                print("Result-stats:")
                print(" Tweaked Z-axis: \t{}".format(x.alignment))
                print(" Axis {}, \tangle: {}".format(x.rotation_axis, x.rotation_angle))
                print(""" Rotation matrix: 
                {:2f}\t{:2f}\t{:2f}
                {:2f}\t{:2f}\t{:2f}
                {:2f}\t{:2f}\t{:2f}""".format(x.matrix[0][0], x.matrix[0][1], x.matrix[0][2],
                                              x.matrix[1][0], x.matrix[1][1], x.matrix[1][2],
                                              x.matrix[2][0], x.matrix[2][1], x.matrix[2][2]))
                print(" Unprintability: \t{}".format(x.unprintability))

                print("Found result:    \t{:2f} s\n".format(time() - cstime))

                ret = np.array(x.matrix).reshape(-1).tolist()
                # print(type(ret[0]))


    # if not args.result:
    #     try:
    #         FileHandler.write_mesh(objs, info, args.outputfile, args.output_type)
    #     except FileNotFoundError:
    #         raise FileNotFoundError("Output File '{}' not found.".format(args.outputfile))

    # try:
    #     print(args.outputfile)
    #     FileHandler.write_mesh(objs, info, args.outputfile, args.output_type)
    # except FileNotFoundError:
    #     raise FileNotFoundError("Output File '{}' not found.".format(args.outputfile))

    # Success message
    if args.verbose:
        print("Tweaking took:  \t{:2f} s".format(time() - stime))
        print("Successfully Rotated!")
    del x
    del args
    return ret

# if __name__ == "__main__":
#     cli()
