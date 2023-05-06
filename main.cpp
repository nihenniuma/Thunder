#include "crossroads.h"

using namespace pybind11::literals;

py::scoped_interpreter guard{};
py::dict kwargs = py::dict( "inputfile"_a="ghost.stl",
                            "outputfile"_a="ghost_tweaked.stl",
                            "verbose"_a=0,
                            "show_progress"_a=0,
                            "convert"_a=0,
                            "output_type"_a="binarystl",
                            "extended_mode"_a=0,
                            "version"_a=0,
                            "result"_a=1,
                            "favside"_a="",
                            "minimize"_a="vol",
                            "volume"_a="");
py::object args = py::module_::import("Tweaker").attr("ARGS")(kwargs);
py::object run_tweaker = py::module_::import("Tweaker").attr("run");

int main()
{
    std::string input("/mnt/e/codespace/tweaker/build/plater.conf");
    tweak(input);
    system("/mnt/e/Optimizer/Plater/plater/build/plater plater_tweaked.conf");
    return 0;
}
