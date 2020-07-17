# -*- coding: utf-8 -*-
import argparse
import os

from context2yaml.modulemd import Modulemd


def get_load_module_stream(yaml_file_path, module_name, stream_name):
    module_stream = Modulemd.ModuleStream.read_file(
        yaml_file_path, True, module_name, stream_name)

    v2_stream = module_stream.upgrade(Modulemd.ModuleStreamVersionEnum.TWO)
    v2_stream.validate()

    return v2_stream

def create_module_stream_dir(result_dir_path, module_name, stream_name):
    module_stream_dir = "{name}:{stream}".format(name=module_name, stream=stream_name)
    abs_result_dir_path = os.path.abspath(result_dir_path)
    module_stream_dir_path = os.path.join(abs_result_dir_path, module_stream_dir)
    os.mkdir(module_stream_dir_path, 0o755)

    return module_stream_dir_path

def write_module_stream_context_yaml_file(mmd, stream_dir_path, module_name, stream_name):
    index = Modulemd.ModuleIndex()
    index.add_module_stream(mmd)
    context = mmd.get_context()

    file_name = "{name}:{stream}:{context}.yaml".format(
        name=module_name,
        stream=stream_name,
        context=context,
    )

    abs_file_path = os.path.join(stream_dir_path, file_name)

    with open(abs_file_path, "w") as fd:
        fd.write(index.dump_to_string())

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml", 
                        type=str, 
                        required=True,
                        action="store",
                        dest="yaml_file_path",
                        help="Path to the modulemd yaml path.")
    parser.add_argument("--name", 
                        type=str, 
                        required=True,
                        action="store",
                        dest="module_name",
                        help="Name of the module.")
    parser.add_argument("--stream", 
                        type=str, 
                        required=True,
                        action="store",
                        dest="stream_name",
                        help="Name of the stream.")
    parser.add_argument("--output -o", 
                        type=str, 
                        action="store",
                        dest="result_dir_path",
                        help="Where the results will be stored.",
                        default="./")


    return parser.parse_args()

def main():
    args = parse_arguments()

    mmd = get_load_module_stream(args.yaml_file_path, args.module_name, args.stream_name)

    xmd = mmd.get_xmd()

    if not xmd:
        raise Exception("The 'xmd' property of the modulemd yaml file is empty!")

    if "contexts" not in xmd:
        raise KeyError(("The 'xmd' property of the modulemd yaml file does not containt the"
                        " 'contexts' key."))

    result_dir_path = create_module_stream_dir(args.result_dir_path, args.module_name,
                                               args.stream_name)

    for context, dependencies in xmd["contexts"].items():
        mmd.set_context(context)

        if "buildrequires" not in dependencies:
            raise KeyError("The  context '{context}' is missing the 'buildrequires' key!".format(
                context=context))

        if "requires" not in dependencies:
            raise KeyError("The context '{context}' is missing the 'requires' key!".format(
                context=context))

        old_module_debs = mmd.get_dependencies()
        for deps in old_module_debs:
            mmd.remove_dependencies(deps)

        module_debs = Modulemd.Dependencies.new()

        for module, stream in dependencies["buildrequires"].items():
            module_debs.add_buildtime_stream(module, stream)

        for module, stream in dependencies["requires"].items():
            module_debs.add_runtime_stream(module, stream)

        mmd.add_dependencies(module_debs)

        write_module_stream_context_yaml_file(mmd, result_dir_path, args.module_name,
                                              args.stream_name)
