import ast
import argparse
import sys

from .parser import Parser
from .pygen import PythonGenerator
from .pypr import to_source
from .pseudo import to_pseudo
from .incgen import gen_inc_module
from .utils import is_valid_debug_level, set_debug_level

stdout = sys.stdout
stderr = sys.stderr


def dpyast_from_file(filename):
    """Generates a DistPy AST representation from the specified DistPy source
       file.

    """
    dt = Parser(filename)
    with open(filename, 'r') as infd:
        pytree = ast.parse(infd.read())
        dt.visit(pytree)
        stderr.write("%s compiled with %d errors and %d warnings.\n" %
                     (filename, dt.errcnt, dt.warncnt))
        if dt.errcnt == 0:
            return dt.program
        else:
            return None

def dpyfile_to_pyast(filename):
    """Translates the given DistPy source file into Python code. Returns an AST
       representation of the result.

    """
    dpyast = dpyast_from_file(filename)
    if dpyast is None:
        stderr.write("Error: unable to generate DistPy AST for file %s\n" % filename)
        return None

    pyast = PythonGenerator(filename).visit(dpyast)
    if pyast is None:
        stderr.write("Error: unable to generate Python AST for file %s\n" % filename)
        return None
    else:
        return pyast

def dpyfile_to_pseudofile(filename, outname=None):
    """Compiles a DistPy source file to Python file.

    'filename' is the input DistPy source file. Optional parameter 'outname'
    specifies the file to write the result to. If 'outname' is None the
    filename is inferred by replacing the suffix of 'filename' with '.py'.

    """
    purename, _, suffix = filename.rpartition(".")
    if len(purename) == 0:
        purename = suffix
        suffix = ""
    if suffix == "py":
        stderr.write("Warning: skipping '.py' file %s\n" % filename)
        return
    elif suffix != "dpy":
        stderr.write("Warning: unknown suffix '%s' in filename '%s'\n" %
                      (suffix, filename))

    dpyast = dpyast_from_file(filename)
    psdstr = to_pseudo(dpyast)
    if outname is None:
        outname = purename + ".da"
    with open(outname, "w") as outfd:
        outfd.write(psdstr)
        stderr.write("Written pseudo code file %s.\n"% outname)

def dpyfile_to_pyfile(filename, outname=None):
    """Compiles a DistPy source file to Python file.

    'filename' is the input DistPy source file. Optional parameter 'outname'
    specifies the file to write the result to. If 'outname' is None the
    filename is inferred by replacing the suffix of 'filename' with '.py'.

    """
    purename, _, suffix = filename.rpartition(".")
    if len(purename) == 0:
        purename = suffix
        suffix = ""
    if suffix == "py":
        stderr.write("Warning: skipping '.py' file %s\n" % filename)
        return
    elif suffix != "dpy":
        stderr.write("Warning: unknown suffix '%s' in filename '%s'\n" %
                      (suffix, filename))

    pyast = dpyfile_to_pyast(filename)

    if pyast is not None:
        pystr = to_source(pyast)
        if outname is None:
            outname = purename + ".py"
        with open(outname, "w") as outfd:
            outfd.write(pystr)
            stderr.write("Written compiled file %s.\n"% outname)

def check_python_version():
    if sys.version_info < (3, 3):
        stderr.write("DistPy requires Python version 3.3 or newer.\n")
        return False
    elif sys.version_info > (3, 5):
        stderr.write("Python 3.5 not yet supported.\n")
        return False
    else:
        return True

def dpyfile_to_incfiles(args):
    filename = args.infile
    outname = args.outfile
    purename, _, suffix = filename.rpartition(".")
    if len(purename) == 0:
        purename = suffix
        suffix = ""
    if suffix == "py":
        stderr.write("Warning: skipping '.py' file %s\n" % filename)
        return
    elif suffix != "dpy":
        stderr.write("Warning: unknown suffix '%s' in filename '%s'\n" %
                      (suffix, filename))
    dpyast = dpyast_from_file(filename)
    module_name = purename + "_inc"
    module_filename = module_name + ".py"
    if dpyast is not None:
        inc, ast = gen_inc_module(dpyast, args.__dict__)
        incstr = to_source(inc)
        aststr = to_source(ast)
        if outname is None:
            outname = purename + ".py"
        with open(outname, "w") as outfd:
            outfd.write(aststr)
            stderr.write("Written compiled file %s.\n"% outname)
        with open(module_filename, "w") as outfd:
            outfd.write(incstr)
            stderr.write("Written interface file %s.\n" % module_filename)

def main(argv=None):
    """Main entry point when invoking compiler module from command line.
    """
    if not check_python_version():
        return 2

    ap = argparse.ArgumentParser(description="DistPy compiler.")
    ap.add_argument('-o', help="Output file name.", dest="outfile")
    ap.add_argument('-L', help="Logging output level.",
                    dest="debug", default=None)
    ap.add_argument('-p', help="Generate pseudo code instead of Python code.",
                    action='store_true', dest="genpsd")
    ap.add_argument('-i',
                    help="Generate interface code for plugging"
                    " into incrementalizer.",
                    action='store_true', dest="geninc")
    ap.add_argument('--no-table1',
                    help="Disable table 1 quantification transformations. "
                    "Only useful with '-i'.",
                    action='store_true', dest="notable1")
    ap.add_argument('--no-table2',
                    help="Disable table 2 quantification transformations. "
                    "Only useful with '-i'.",
                    action='store_true', dest="notable2")
    ap.add_argument('--no-table3',
                    help="Disable table 3 quantification transformations. "
                    "Only useful with '-i'.",
                    action='store_true', dest="notable3")
    ap.add_argument('--jb-style',
                    help="Generate Jon-friendly quantification transformations. "
                    "Only useful with '-i'.",
                    action='store_true', dest="jbstyle")
    ap.add_argument('--no-all-tables',
                    help="Disable all quantification transformations. "
                    "Only useful with '-i'.",
                    action='store_true', dest="noalltables")
    ap.add_argument('--psdfile', help="Name of output pseudo code file.",
                    dest="psdfile", default=None)
    ap.add_argument('infile', metavar='SOURCEFILE', type=str,
                    help="DistPy input source file.")

    if argv is None:
        argv = sys.argv[1:]
    args = ap.parse_args(argv)
    if args.debug is not None:
        try:
            level = int(args.debug)
            if is_valid_debug_level(level):
                set_debug_level(level)
            else:
                raise ValueError()
        except ValueError:
            stderr.write("Invalid debugging level %s.\n" % str(args.debug))

    if args.genpsd:
        dpyfile_to_pseudofile(args.infile, args.psdfile)
    elif args.geninc:
        dpyfile_to_incfiles(args)
    else:
        dpyfile_to_pyfile(args.infile, args.outfile)

    return 0
