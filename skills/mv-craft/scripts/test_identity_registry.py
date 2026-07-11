#!/usr/bin/env python3
import json
import os
import tempfile
import unittest

import identity_registry as registry


class IdentityRegistryTest(unittest.TestCase):
    def test_registry_is_project_driven(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "设定", "characters"))
            os.makedirs(os.path.join(root, "设定", "locations"))
            os.makedirs(os.path.join(root, "分镜"))
            with open(os.path.join(root, "视觉蓝图.md"), "w", encoding="utf-8") as f:
                f.write("- global_style: 复古舞台电影感\n- palette_anchor: 红 #aa0000, 金 #ffaa00\n")
            with open(os.path.join(root, "设定", "characters", "主唱林夏.md"), "w", encoding="utf-8") as f:
                f.write("# 角色卡 — 林夏\n- 固定外貌：黑色短发、凤眼\n- 固定服装：红色舞台夹克\n- 形态变体：舞台态；后台态\n")
            with open(os.path.join(root, "设定", "locations", "场景.md"), "w", encoding="utf-8") as f:
                f.write("## 旧剧院舞台\n红色帷幕、钨丝灯和木地板\n")
            ident = registry.build_identity_registry(root)
            assets = registry.build_asset_registry(root)
            self.assertEqual(ident["identities"][0]["display_name"], "主唱林夏")
            self.assertIn("复古舞台", ident["global_style"])
            self.assertEqual(len(ident["identity_states"]), 2)
            self.assertEqual(assets["assets"][0]["name"], "旧剧院舞台")
            payload = json.dumps({"identity": ident, "assets": assets}, ensure_ascii=False)
            self.assertNotIn("青锋", payload)
            self.assertNotIn("仗剑", payload)


if __name__ == "__main__":
    unittest.main()
