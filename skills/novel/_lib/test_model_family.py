import unittest
from model_family import model_family

class TestModelFamily(unittest.TestCase):
    def test_model_family(self):
        self.assertEqual(model_family('gpt-4o-mini'), 'openai')
        self.assertEqual(model_family('claude-3-5-sonnet'), 'anthropic')
        self.assertEqual(model_family('gemini-1.5-pro'), 'google')
        self.assertEqual(model_family('doubao-pro'), 'bytedance')
        self.assertEqual(model_family('qwen-max'), 'alibaba')
        self.assertEqual(model_family('hunyuan-pro'), 'tencent')
        self.assertEqual(model_family('ernie-4.0'), 'baidu')
        self.assertEqual(model_family('minimax-abab6'), 'minimax')
        self.assertEqual(model_family('kling-v1'), 'kuaishou')
        self.assertEqual(model_family('unknown-model'), '')
        self.assertEqual(model_family(None), '')

if __name__ == '__main__':
    unittest.main()

