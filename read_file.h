#include <iostream>
#include <istream>
#include <fstream>
#include <string>
#include <algorithm>
#include <Eigen/Dense>
#include <vector>

using namespace std;

inline void trans2lower(string& s){ // transform word to lower
    for(int i = 0; i < s.length(); i++){
        if(s[i] >= 65 && s[i] <= 90) s[i] -= 32;
    }
}

/*
    put file_path and model to store STL information.
    return success or not.

    Matrix:
    row 
    0   - normal coordinate
    1   - first vertex coordinate
    2   - second vertex coordinate
    3   - third vertex coordinate
    four rows represent one facet
*/
bool readSTLFile(const string file_path, Eigen::MatrixX3f& model, Eigen::MatrixX3f& normals);

/*
    read file paths from config(.conf) file.
    return vector<string> includes many file paths. 
*/
inline vector<string> readConfig(string config_path){
    ifstream in;
    in.open(config_path, ios::in);
    vector<string> ret;
    while(!in.eof()){
        char buf[1024];
        in.getline(buf, sizeof(buf));
        if(strcmp(buf, "\0") == 0) continue; // 防止在conf中输入很多行文件地址以后回车多了一个空行
        // cout << buf << endl;
        // cout << "out" << endl;
        ret.push_back(string(buf));
    }
    in.close();
    return ret;
}