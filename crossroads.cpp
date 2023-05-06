# include "crossroads.h"

// Eigen::Matrix3f useFunction(map<string, bool> arguments, map<string, string> file_info)
Eigen::Matrix3f useFunction(string inputfile, string temp)
{
    using namespace pybind11::literals;

    // py::scoped_interpreter guard{}; // start the interpreter and keep it alive
    // kwargs = py::dict(  "inputfile"_a=file_info["inputfile"],
    //                     "outputfile"_a=file_info["outputfile"],
    //                     "verbose"_a=arguments["verbose"],
    //                     "show_progress"_a=arguments["show_progress"],
    //                     "convert"_a=arguments["convert"],
    //                     "output_type"_a=file_info["output_type"],
    //                     "extended_mode"_a=arguments["extended_mode"],
    //                     "version"_a=arguments["version"],
    //                     "result"_a=arguments["result"],
    //                     "favside"_a=file_info["favside"],
    //                     "minimize"_a=file_info["minimize"],
    //                     "volume"_a=arguments["volume"]);

    // args = py::module_::import("Tweaker").attr("ARGS")(kwargs);
    // run_tweaker = py::module_::import("Tweaker").attr("run");
    args.attr("inputfile") = inputfile;
    args.attr("outfile") = temp;
    py::list ret = run_tweaker(args);
    vector<float> res = ret.cast<vector<float>>();
    Eigen::Matrix3f rotation;
    rotation << res[0], res[1], res[2],
                res[3], res[4], res[5], 
                res[6], res[7], res[8];
    // cout << rotation;
    return rotation;
}

bool writeTweakedModel(Eigen::MatrixX3f& model, Eigen::MatrixX3f& normals, Eigen::Matrix3f rotation, string file_path){
    ofstream fout(file_path, ios::out | ios::binary);
    model = model*rotation;
    normals = normals*rotation.transpose();
    char head[80] = {0};
    fout.write(head, 80);
    int rows = normals.rows();
    fout.write((char*)&rows, sizeof(rows));
    for(int i = 0; i < rows; ++i){
        for(int j = 0; j < 3; j++){
            float tmp = normals(i, j);
            fout.write((char*)&tmp, sizeof(tmp));
        }
        for(int j = 0; j < 3; j++){
            float tmp = model(3*i+0, j);
            fout.write((char*)&tmp, sizeof(tmp));
        }
        for(int j = 0; j < 3; j++){
            float tmp = model(3*i+1, j);
            fout.write((char*)&tmp, sizeof(tmp));
        }
        for(int j = 0; j < 3; j++){
            float tmp = model(3*i+2, j);
            fout.write((char*)&tmp, sizeof(tmp));
        }
        short attribute_byte_count = 0;
        fout.write((char*)&attribute_byte_count, sizeof(attribute_byte_count));
    }
    fout.close();
    return 1;
}

bool tweak(string config_path){
    vector<string> file_paths_list = readConfig(config_path);
    if(file_paths_list.size() == 0){
        cerr << "None STL file read!" << endl;
        return 0;
    }
    map<string, string> file_info;
    for(int i = 0; i < file_paths_list.size(); ++i){
        string file_path = file_paths_list[i];
        string temp = file_path.substr(0, file_path.length() - 4);
        temp += "_tweaked.stl"; // we append this to all tweaked files
        Eigen::Matrix3f rotation = useFunction(file_path, temp);
        Eigen::MatrixX3f model;
        Eigen::MatrixX3f normals;
        bool isSuccess = readSTLFile(file_path, model, normals);
        if(isSuccess == false) continue;
        writeTweakedModel(model, normals, rotation, temp);
    }
    return 1;
}
