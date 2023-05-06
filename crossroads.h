# include <pybind11/embed.h>
# include <pybind11/numpy.h>
# include <pybind11/stl.h>
# include <string>
# include <map>
# include <iostream>
# include <fstream>
# include <vector>
# include <Eigen/Dense>
# include <cstdlib>
# include "read_file.h"

namespace py = pybind11;
using namespace std;

extern py::dict kwargs;
extern py::object args;
extern py::object run_tweaker;

/*
    input arguments and file_info to python.
    get a rotation matrix.
*/
// Eigen::Matrix3f useFunction(map<string, bool> arguments, map<string, string> file_info);
Eigen::Matrix3f useFunction(string inputfile, string temp);

/*
    input untweaked model matrix and roration, then matrix*rotation.
    modify untweaked model to tweaked model and write it to *filename*_tweaked.stl.
*/
bool writeTweakedModel(Eigen::MatrixX3f& model, Eigen::MatrixX3f& normals, Eigen::Matrix3f rotation, std::string file_path);

/*
    The overall process of integrating all the above functions.
*/
bool tweak(std::string config_path);