"""Host bootstrap contracts: python3 -B tests/project-files.py."""
from pathlib import Path
import sys
import os
import subprocess
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from project import ensure_project_files, ROOT_CMAKE, SRC_CMAKE, LEGACY_SRC_CMAKE, arduino_component_name


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'project with spaces'
        self.src = self.root / 'src'
        self.src.mkdir(parents=True)
        (self.src / 'main.cpp').write_text('void setup() {} void loop() {}')

    def run_bootstrap(self):
        ensure_project_files(self.root, self.src)

    def test_fresh_and_incremental(self):
        self.run_bootstrap()
        for path, expected in [(self.root / 'CMakeLists.txt', ROOT_CMAKE),
                               (self.src / 'CMakeLists.txt', SRC_CMAKE)]:
            self.assertEqual(path.read_text(), expected)
            stamp = path.stat().st_mtime_ns
            self.run_bootstrap()
            self.assertEqual(path.stat().st_mtime_ns, stamp)

    def test_explicit_example_preserved(self):
        example = Path(__file__).resolve().parents[1] / 'examples/bluetooth-pin'
        for target, source in [(self.root, example), (self.src, example / 'src')]:
            (target / 'CMakeLists.txt').write_bytes((source / 'CMakeLists.txt').read_bytes())
        before = [(p, p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.root.rglob('CMakeLists.txt')]
        self.run_bootstrap()
        for path, content, stamp in before:
            self.assertEqual(path.read_bytes(), content)
            self.assertEqual(path.stat().st_mtime_ns, stamp)

    def test_negative_root_preserved_no_partial_creation(self):
        for text in ['project(unsafe)\n',
                     ROOT_CMAKE.replace('include("${RCDEV_DIR}', '#include("${RCDEV_DIR}'),
                     ROOT_CMAKE + 'set(CONFIG_BT_SSP_ENABLED ON)\n',
                     ROOT_CMAKE.replace('project(rcdev)\n', '').replace(
                         'cmake_minimum_required', 'project(rcdev)\ncmake_minimum_required'),
                     ROOT_CMAKE.replace('project(rcdev)', 'project(rcdev)\nreturn()')]:
            with self.subTest(text=text):
                path = self.root / 'CMakeLists.txt'
                path.write_text(text)
                with self.assertRaisesRegex(ValueError, 'File preserved'):
                    self.run_bootstrap()
                self.assertEqual(path.read_text(), text)
                self.assertFalse((self.src / 'CMakeLists.txt').exists())

    def test_negative_component_preserved(self):
        path = self.src / 'CMakeLists.txt'
        path.write_text('idf_component_register(SRCS "main.cpp")\n')
        with self.assertRaisesRegex(ValueError, 'REQUIRES'):
            self.run_bootstrap()
        self.assertFalse((self.root / 'CMakeLists.txt').exists())
        self.assertEqual(path.read_text(), 'idf_component_register(SRCS "main.cpp")\n')

    def test_exact_legacy_migration(self):
        (self.root / 'CMakeLists.txt').write_text(ROOT_CMAKE)
        path = self.src / 'CMakeLists.txt'
        path.write_text(LEGACY_SRC_CMAKE)
        root_stamp = (self.root / 'CMakeLists.txt').stat().st_mtime_ns
        self.run_bootstrap()
        self.assertEqual(path.read_text(), SRC_CMAKE)
        self.assertEqual((self.root / 'CMakeLists.txt').stat().st_mtime_ns, root_stamp)
        stamp = path.stat().st_mtime_ns
        self.run_bootstrap()
        self.assertEqual(path.stat().st_mtime_ns, stamp)

    def test_modified_legacy_preserved(self):
        path = self.src / 'CMakeLists.txt'
        text = LEGACY_SRC_CMAKE + '# user customization\n'
        path.write_text(text)
        with self.assertRaises(ValueError):
            self.run_bootstrap()
        self.assertEqual(path.read_text(), text)
        self.assertFalse((self.root / 'CMakeLists.txt').exists())

    def test_legacy_not_migrated_when_root_invalid(self):
        (self.root / 'CMakeLists.txt').write_text('project(custom)\n')
        path = self.src / 'CMakeLists.txt'
        path.write_text(LEGACY_SRC_CMAKE)
        with self.assertRaises(ValueError):
            self.run_bootstrap()
        self.assertEqual(path.read_text(), LEGACY_SRC_CMAKE)

    def test_old_explicit_custom_contract_preserved(self):
        path = self.src / 'CMakeLists.txt'
        text = 'idf_component_register(SRCS "main.cpp" INCLUDE_DIRS "." REQUIRES framework-arduinoespressif32)\n'
        path.write_text(text)
        with self.assertRaisesRegex(ValueError, 'File preserved'):
            self.run_bootstrap()
        self.assertEqual(path.read_text(), text)
        self.assertFalse((self.root / 'CMakeLists.txt').exists())

    def test_invalid_component_name(self):
        for name in ['framework-arduinoespressif32@4.20017', 'package;extra', 'package with spaces']:
            with self.assertRaisesRegex(ValueError, 'not CMake-compatible'):
                arduino_component_name('/packages/' + name)

    def test_identity_canonical_versioned_and_mismatch(self):
        resolver = Path(__file__).resolve().parents[1] / 'cmake/arduino-component.cmake'
        cmake = os.environ.get('CMAKE', 'cmake')
        for name in ['framework-arduinoespressif32',
                     'framework-arduinoespressif32-4.20017.260907+sha.dcc1105b']:
            with self.subTest(name=name):
                package = self.root / name
                self.assertEqual(arduino_component_name(package), name)
                package.mkdir()
                (package / 'CMakeLists.txt').write_text('# mock package')
                script = self.root / 'identity.cmake'
                script.write_text('''function(idf_component_get_property out component property)
  get_filename_component(expected "$ENV{DEVRABIT_ARDUINO_DIR}" NAME)
  if(NOT component STREQUAL expected OR NOT property STREQUAL "COMPONENT_DIR")
    message(FATAL_ERROR "Wrong component lookup")
  endif()
  set(${out} "$ENV{REGISTERED_DIR}" PARENT_SCOPE)
endfunction()
include("''' + resolver.as_posix() + '''")
get_filename_component(expected "$ENV{DEVRABIT_ARDUINO_DIR}" NAME)
if(NOT DEVRABIT_ARDUINO_COMPONENT STREQUAL expected)
  message(FATAL_ERROR "Wrong identity")
endif()
''')
                environment = dict(os.environ, DEVRABIT_ARDUINO_DIR=str(package), REGISTERED_DIR=str(package))
                subprocess.run([cmake, '-P', str(script)], env=environment, check=True)
                environment['REGISTERED_DIR'] = str(self.src)
                result = subprocess.run([cmake, '-P', str(script)], env=environment, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('does not match', result.stderr)

    def test_partial_supported_project(self):
        (self.root / 'CMakeLists.txt').write_text(ROOT_CMAKE)
        self.run_bootstrap()
        self.assertEqual((self.src / 'CMakeLists.txt').read_text(), SRC_CMAKE)


if __name__ == '__main__':
    unittest.main()
