import shlex
import subprocess
import unittest
from xml.dom.minidom import parse

import re
import os
this_dir = os.path.dirname(os.path.realpath(__file__))
log_path = os.getcwd() + os.sep + "po_log.txt"


class BaseTestCase(unittest.TestCase):
    """
    Base class Robot page object test cases.
    """

    def setUp(self):

        try:
            os.unlink(log_path)
        except OSError:
            pass

        # Unset all PO_ env variables, but save them so we can restore them in teardown
        self.original_po_vars = {}
        for key in os.environ.keys():
            if key.startswith("PO_"):
                self.original_po_vars[key] = os.environ[key]
                del os.environ[key]

    def tearDown(self):
        # Restore envs
        for key in self.original_po_vars:
            os.environ[key] = self.original_po_vars[key]

        try:
            os.unlink(log_path)
        except OSError:
            pass

    def run_program(self, program, *args, **opts):

        """
        Runs a program using a subprocess, returning an object with the following properties:

        - cmd: The command run after splitting with shlex.
        - returncode: The return code
        - output: the ouput to stdout or stderr

        In the case where a simple flag needs to be passed, psss the option as a boolean, eg::
            self.runsanity("http://www.example.com", no_page_check=True)

        :url args: The arguments to pass to sanity. Either a single URL,
            multiple URLS, or a URL/path to the URLs XML file

        :url: opts: Keywords of options to sanity. Use underscores in place of dashes.
        """

        class Ret(object):
            """
            The object to return from running the program
            """
            def __init__(self, cmd, returncode, output, rid, xmldoc=None):
                self.cmd = cmd
                self.returncode = returncode
                self.output = output
                self.rid = rid
                self.xmldoc = xmldoc

            def __repr__(self):
                return "<run object: cmd: '%s', returncode: %s, rid: %s, xmldoc: %s, output: %s>" % (self.cmd,
                                                                                               self.returncode,
                                                                                               self.rid, self.xmldoc,
                                                                                               self.output[0:25]
                                                                                               .replace("\n", ""))

        cmd = program + " " + " ".join(args) + " "

        for name in opts:
            val = opts[name]
            if isinstance(val, bool):
                cmd = cmd + "--" + name.replace("_", "-") + " "
            else:
                cmd = cmd + "--" + name.replace("_", "-") + "=" + val + " "

        p = subprocess.Popen(shlex.split(cmd), shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        com = p.communicate()
        code = p.wait()

        # Check the xml file path. If it's passed, use it, otherwise it's
        # the sanity directory + /sanity.xml
        xml_file_path_opt = None
        if code == 0 and "xml" in opts:
            for name in opts:
                if name == "xml_file":
                    xml_file_path_opt = opts[name]

            xml_file_path = xml_file_path_opt if xml_file_path_opt else self.sanity_dir + "/sanity.xml"
            f = open(xml_file_path, "r")
            dom = parse(f)
        else:
            dom = None

        # Out is either stdout, or stderr
        out = com[0] if com[1] == "" else com[1]
        # Splice out trailing new line
        out = out[:-1]

        first_line = out.split("\n")[0]
        rid = re.sub(".*Run ID: ", "", first_line.replace("\n", ""))
        if len(rid) != 9:
            rid = None

        return Ret(cmd, code, out, rid, xmldoc=dom)

    def assert_run(self, run,
                          expected_returncode=0, expected_tests_ran=None,
                          expected_tests_failed=None,
                          search_output=None, expected_browser=None
    ):
        """
        Makes general assertions about a program run based on return code
        and strings written to stdout. Always checks if run was 0
        return code.

        :param run: The object returned by runsanity()
        :param expected_returncode: expected returncode
        :param expected_tests_ran: number of tests ran
        :param expected_tests_failed: number of tests failed
        :param search_output: Text to assert is present in stdout of run. Provide  regular expression
        """
        returncode = run.returncode

        self.assertEquals(expected_returncode, returncode,
                          "Return code was %s, expecting %s with the command: '%s'" % (
                              returncode, expected_returncode, run.cmd))
        if expected_tests_ran:
            self.assertTrue("Ran %s test" % expected_tests_ran in run.output, "Didn't get %s tests ran when "
                                                                                    "running '%s'" % (
                                                                                        expected_tests_ran,
                                                                                        run.cmd))
        if expected_tests_failed:
            self.assertTrue("failures=%s" % expected_tests_failed in run.output,
                            "Did not find %s expected failures when running %s." % (expected_tests_failed,
                                                                                    run.cmd))
        if search_output:
            self.assertIsNotNone(re.search(search_output, run.output),
                                 "string: '%s' not found in stdout when running %s" % (
                                     search_output, run.cmd))

        if expected_browser:
            if "pybot" in run.cmd:
                try:
                    robot_log = open(os.getcwd() + os.sep + "log.html")
                    self.assertTrue(expected_browser in robot_log.read(), "Unexpected browser. Expected %s, got something else")
                finally:
                    robot_log.close()
            else:
                try:
                    po_log = open(log_path)
                    log_fields = po_log.read().split("\t")
                    logged_browser = log_fields[2]
                    self.assertTrue(expected_browser.lower() in logged_browser.lower(), "Unexpected browser. Expected %s, "
                                                                                   "got %s" % (expected_browser,
                                                                                               logged_browser))
                finally:
                    po_log.close()


