import importlib.util
from pathlib import Path
import plistlib
import stat
import struct
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location(
    "packager", Path(__file__).with_name("package_unsigned_ipa.py")
)
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "Runner.app"
        self.app.mkdir()
        self.info = {
            "CFBundleIdentifier": packager.BUNDLE_ID,
            "CFBundleShortVersionString": "1.2.2", "CFBundleVersion": "1",
            "CFBundleExecutable": "Runner.exe", "MinimumOSVersion": "15.0",
            **{key: "Permission description" for key in packager.PRIVACY_KEYS},
        }
        (self.app / "Info.plist").write_bytes(plistlib.dumps(self.info))
        # The suffix lets Windows stat() represent executable permission as well.
        self.executable = self.app / "Runner.exe"
        self.write_executable(platform=2)
        self.executable.chmod(0o755)
        framework = self.app / "Frameworks/App.framework"
        framework.mkdir(parents=True)
        (framework / "App").write_bytes(b"fixture framework")
        self.output = self.root / "output.ipa"

    def write_executable(self, platform):
        self.executable.write_bytes(
            struct.pack("<8I", 0xFEEDFACF, 0x0100000C, 0, 2, 1, 24, 0, 0)
            + struct.pack("<6I", 0x32, 24, platform, 0, 0, 0)
        )

    def test_packages_device_build_and_writes_metadata_and_checksum(self):
        result = packager.package(self.app, self.output)
        self.assertEqual(result["architecture"], "arm64")
        self.assertFalse(result["signed"])
        self.assertTrue(self.output.with_suffix(".ipa.sha256").is_file())
        self.assertTrue(self.output.with_suffix(".build.json").is_file())
        self.assertEqual(packager.validate_ipa(self.output)["CFBundleVersion"], "1")

    def test_rejects_simulator_binary(self):
        self.write_executable(platform=7)
        with self.assertRaisesRegex(ValueError, "not built for an iOS device"):
            packager.package(self.app, self.output)

    def test_rejects_missing_privacy_description(self):
        del self.info["NSCameraUsageDescription"]
        (self.app / "Info.plist").write_bytes(plistlib.dumps(self.info))
        with self.assertRaisesRegex(ValueError, "Missing privacy"):
            packager.package(self.app, self.output)

    def test_rejects_missing_flutter_framework(self):
        (self.app / "Frameworks/App.framework/App").unlink()
        with self.assertRaisesRegex(ValueError, "Missing Flutter"):
            packager.package(self.app, self.output)

    def test_preserves_symlinks(self):
        link = self.app / "Frameworks/App.framework/Alias"
        try:
            link.symlink_to("App")
        except OSError:
            self.skipTest("Creating symlinks requires permission on this system")
        packager.package(self.app, self.output)
        with zipfile.ZipFile(self.output) as archive:
            entry = archive.getinfo("Payload/Runner.app/Frameworks/App.framework/Alias")
            self.assertTrue(stat.S_ISLNK(entry.external_attr >> 16))
            self.assertEqual(archive.read(entry), b"App")


if __name__ == "__main__":
    unittest.main()
