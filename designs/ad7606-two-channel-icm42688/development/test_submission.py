import json,tempfile,unittest
from pathlib import Path
from check_submission import review
class SubmissionTests(unittest.TestCase):
 def test_missing_is_not_pass(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(review(d)['status'],'INCOMPLETE')
 def test_blank_stage_has_no_approval(self):
  r=review(Path(__file__).parent/'03');self.assertTrue(r['issues']);self.assertFalse(r['engineering_approval'])
 def test_complete_inventory_still_needs_review(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'photo.txt').write_text('test fixture, not physical evidence')
   data=dict(stage=0,build='ad7606-two-channel-icm42688',hardware_revision='test',operator='test',date='2026-10-04',changes_since_last_stage='initial',instrument_list=['DMM'],evidence_files=['photo.txt'])
   (p/'submission.json').write_text(json.dumps(data));r=review(p)
   self.assertEqual(r['status'],'READY FOR HUMAN REVIEW');self.assertFalse(r['engineering_approval']);self.assertEqual(len(r['sha256']['photo.txt']),64)
 def test_path_escape_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'submission.json').write_text(json.dumps({'stage':0,'evidence_files':['../outside']}));self.assertTrue(any('outside' in x for x in review(p)['issues']))
 def test_bad_stage_does_not_crash(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'submission.json').write_text(json.dumps({'stage':'three'}));self.assertEqual(review(p)['status'],'INCOMPLETE')
if __name__=='__main__':unittest.main()
