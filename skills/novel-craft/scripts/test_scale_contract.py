#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scale band contract tests for novel init scripts.

Can run without pytest:
    python3 skills/novel-craft/scripts/test_scale_contract.py
"""
import importlib.util
import os
import sys
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)

import contract


def load_script(relpath):
    path = os.path.join(REPO, relpath)
    spec = importlib.util.spec_from_file_location(relpath.replace("/", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    prev_contract = sys.modules.get("contract")
    sys.modules["contract"] = contract
    try:
        spec.loader.exec_module(mod)
    finally:
        if prev_contract is None:
            sys.modules.pop("contract", None)
        else:
            sys.modules["contract"] = prev_contract
    return mod


class ScaleContractTest(unittest.TestCase):
    def test_scale_profiles_match_split_bands(self):
        scripts = [
            "skills/novel-create/scripts/init_project.py",
            "skills/novel-spinoff/scripts/init_project.py",
            "skills/novel-rewrite/scripts/init_project.py",
        ]
        for relpath in scripts:
            with self.subTest(script=relpath):
                mod = load_script(relpath)
                self.assertIs(mod.SCALE_PROFILE, contract.SCALE_PROFILES)
                self.assertEqual(set(mod.SCALE_PROFILE), set(contract.SCALE_PROFILES))
                got = {k: v["words_per_chapter"] for k, v in mod.SCALE_PROFILE.items()}
                expected = {k: v["words_per_chapter"] for k, v in contract.SCALE_PROFILES.items()}
                self.assertEqual(got, expected)


if __name__ == "__main__":
    unittest.main()
