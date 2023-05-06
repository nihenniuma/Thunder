#include "read_file.h"

bool readSTLFile(const string file_path, Eigen::MatrixX3f& model, Eigen::MatrixX3f& normals){
    string temp = file_path.substr(file_path.length() - 3, 3);
    trans2lower(temp);
    if(temp != "stl"){
        cerr << "false file format!" << endl;
        return false;
    }
    ifstream in;
    in.open(file_path, ios::in);
    if(in.fail()){
        cerr << "file open failed!" << endl;
        return false;
    }

    char buffer_f[5]; // the buffer_f used to distinguish binary stl to ASCII stl
    in.read(buffer_f, 5);
    string s(buffer_f);
    trans2lower(s);
    vector<vector<float>> list;
    vector<vector<float>> norms;
    vector<float> coord(3, 0);
    if(s == "solid") // it's an ASCII file
    {
        string line;
        while (!in.eof())
        {
            Eigen::MatrixX3f model;
            float x, y, z;
            getline(in, line); // facet normal x y z
            const char* c_line = line.c_str(); // transform string to const char* to put it in function sscanf()
            if(sscanf(c_line, " facet normal %f %f %f", &x, &y, &z) == 3)
            {
                coord[0] = x;
                coord[1] = y;
                coord[2] = z;
                norms.push_back(coord);
            }
            else
            {
                cerr << "error: read nromal vector" << endl;
            }
            getline(in, line); // outer loop
            for(int i : {0, 1, 2})
            {
                getline(in, line); // vertex x y z
                c_line = line.c_str(); 
                if(sscanf(c_line, " vertex %f %f %f", &x, &y, &z)==3)
                {
                    coord[0] = x;
                    coord[1] = y;
                    coord[2] = z;
                    list.push_back(coord);
                }
                else
                {
                    int num = sscanf(c_line, " vertex %f %f %f", &x, &y, &z);
                    cerr << "error: coordinate lost! " << 3 - num << "coordiante is needed!" << endl; 
                    return false;
                }
            }
            getline(in, line); // endloop
            getline(in, line); // endfacet
        }
        in.close();
        cout << "ASCII stl file has been loaded successfully!" << endl;
    }else{
        in.close(); // this ifstream was opened in the mode of ios::in, we should open it in binary
        in.open(file_path, ios::in | ios::binary);
        if (in.fail())
        {
            cerr << "error: binary stl file open failed!" << endl;
            return false;
        }
        char head_c[80];
        int num = in.readsome(head_c, 80); // binary stl file has 80 bytes in the front of the file
        if (num != 80)
        {
            cerr << "error: binary stl file error occurs: less than 80 bytes!" << endl;
            cerr << "read" << num << "bytes: " << head_c << endl;
            return false;
        }
        int num_facet;
        in.read((char*)&num_facet, 4); // the first 4 bytes is an unsigned int so do not use atoi
                                      // int num_facets = atoi(buffer_f); 4 bytes int store how many facets are (atoi for char to int)
        cout << "this model has " << num_facet << " facets" << endl;
        list.reserve(9*num_facet);
        norms.reserve(3*num_facet);
        while(!in.eof())
        {
            float x, y, z;
            in.read((char*)&x, 4);
            in.read((char*)&y, 4);
            in.read((char*)&z, 4);
            coord[0] = x;
            coord[1] = y;
            coord[2] = z;
            norms.push_back(coord);

            for(int i = 0; i < 3; i++){
                in.read((char*)&x, 4);
                in.read((char*)&y, 4);
                in.read((char*)&z, 4);
                coord[0] = x;
                coord[1] = y;
                coord[2] = z;
                list.push_back(coord);
            }
            in.read(buffer_f, 2); // two bytes store facet's info
        }
        in.close();

        cout << "binary stl file has been loaded successfully!" << endl;
        cout << "file path: " << file_path << endl;
    }

    // for(int i = 0; i < list.size(); i++){
    //     cout << list[i][0] << ' ' << list[i][1] << ' ' << list[i][2] << endl;
    // }
    // cout << list.size() << endl;
    model.resize(list.size(), 3);
    // cout << list.size() << endl;
    for(int i = 0; i < list.size(); i++){
        model.block<1, 3>(i, 0) << list[i][0], list[i][1], list[i][2];
    }
    list.clear();

    normals.resize(norms.size(), 3);
    // cout << norms.size() << endl;
    for(int i = 0; i < norms.size(); i++){
        normals.block<1, 3>(i, 0) << norms[i][0], norms[i][1], norms[i][2];
    }
    norms.clear();
    return true;
}