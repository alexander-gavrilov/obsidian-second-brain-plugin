import json, os, subprocess, sys, tempfile, unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "resolve_vault.py")


def run(cwd, cfg):
    p = subprocess.run([sys.executable, SCRIPT, "--cwd", cwd, "--config", cfg],
                       capture_output=True, text=True)
    out = dict(l.split("=", 1) for l in p.stdout.splitlines() if "=" in l)
    return p.returncode, out


class T(unittest.TestCase):
    def setUp(self):
        self.d = os.path.realpath(tempfile.mkdtemp())
        self.g = os.path.join(self.d, "global"); self.l = os.path.join(self.d, "local")
        for v in (self.g, self.l):
            os.makedirs(os.path.join(v, "sub")); open(os.path.join(v, "schema.md"), "w").close()
        self.cfg = os.path.join(self.d, "cfg.json")
        json.dump({"global_vault_path": self.g}, open(self.cfg, "w"))
        self.none = os.path.join(self.d, "none"); os.makedirs(self.none)

    def test_inside_global_is_single(self):
        rc, o = run(self.g, self.cfg)
        self.assertEqual((rc, o["mode"], o["root"]), (0, "single", self.g))

    def test_subdir_of_global_is_single(self):
        rc, o = run(os.path.join(self.g, "sub"), self.cfg)
        self.assertEqual((o["mode"], o["root"]), ("single", self.g))

    def test_symlink_to_global_is_single(self):
        link = os.path.join(self.d, "link"); os.symlink(self.g, link)
        rc, o = run(link, self.cfg)
        self.assertEqual(o["mode"], "single")

    def test_local_and_global_ambiguous(self):
        rc, o = run(self.l, self.cfg)
        self.assertEqual((o["mode"], o["root"], o["global"]), ("ambiguous", self.l, self.g))

    def test_outside_uses_global(self):
        rc, o = run(self.none, self.cfg)
        self.assertEqual((rc, o["root"], o["mode"]), (0, self.g, "single"))

    def test_nothing(self):
        rc, o = run(self.none, os.path.join(self.d, "missing.json"))
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
