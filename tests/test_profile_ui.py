import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PersonalFitUITests(unittest.TestCase):
    def test_profile_activation_checkbox_is_not_disabled(self):
        core = (ROOT / 'docs/app-core.js').read_text(encoding='utf-8')
        self.assertIn('input type="checkbox"', core)
        self.assertNotIn('input type="checkbox" disabled', core)
        self.assertIn("profile[e.target.dataset.a].active=e.target.checked", core)

    def test_profile_activation_has_visible_switch_and_label_click_target(self):
        boot = (ROOT / 'docs/bootstrap.js').read_text(encoding='utf-8')
        self.assertIn('installProfileControlsUX', boot)
        self.assertIn('.profileRow input[type=checkbox]', boot)
        self.assertIn("const label=e.target.closest('.profileRow>label')", boot)
        self.assertIn('if(box)box.click()', boot)
        self.assertIn('.profileRow.inactive{opacity:1}', boot)


if __name__ == '__main__':
    unittest.main()
