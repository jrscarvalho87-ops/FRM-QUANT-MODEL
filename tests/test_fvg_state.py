import unittest
from fvg_state import active_fvgs_overlapping_zone as detect

class FvgStateTests(unittest.TestCase):
    def c(self,high,low,ts):return {"ts":ts,"high":high,"low":low,"confirmed":True}

    def test_long_partial_and_full(self):
        bars=[self.c(10,8,0),self.c(11,9,1),self.c(15,12,2)]
        self.assertEqual(len(detect(bars,2,"long",10,13)),1)
        bars.append(self.c(15,11,3))
        f=detect(bars,3,"long",10,13)
        self.assertEqual(len(f),1)
        self.assertEqual(f[0]["active_high"],11)
        bars.append(self.c(13,9,4))
        self.assertEqual(detect(bars,4,"long",10,13),[])

    def test_short_partial_and_full(self):
        bars=[self.c(15,12,0),self.c(14,11,1),self.c(10,8,2)]
        self.assertEqual(len(detect(bars,2,"short",9,12)),1)
        bars.append(self.c(11,8,3))
        f=detect(bars,3,"short",9,12)
        self.assertEqual(f[0]["active_low"],11)
        bars.append(self.c(13,9,4))
        self.assertEqual(detect(bars,4,"short",9,12),[])

    def test_future_mutation_has_no_effect(self):
        bars=[self.c(10,8,0),self.c(11,9,1),self.c(15,12,2),self.c(9,1,3)]
        self.assertEqual(len(detect(bars,2,"long",10,13)),1)

    def test_unconfirmed_rejected_in_prefix(self):
        bars=[self.c(10,8,0),self.c(11,9,1),self.c(15,12,2)]
        bars[2]["confirmed"]=False
        with self.assertRaisesRegex(ValueError,"unconfirmed"):
            detect(bars,2,"long",10,13)

if __name__=="__main__":unittest.main()
