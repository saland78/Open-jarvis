"""Inventory output excludes display identities and never infers performance."""
import json
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import mac_acceleration_inventory as inventory


class InventoryTests(unittest.TestCase):
    def test_only_gpu_fields_from_nested_display_inventory_are_reported(self):
        source={'SPDisplaysDataType':[{'sppci_model':'AMD Example','spdisplays_vram':'4 GB',
                                      'spdisplays_metal':'spdisplays_metal3',
                                      'spdisplays_ndrvs':[{'_spdisplays_display-serial-number':'private'}],
                                      'unrelated':'private'}]}
        result=inventory.gpu_rows(json.dumps(source).encode())
        self.assertEqual(set(result[0]),set(inventory.GPU_FIELDS))
        self.assertNotIn('private',json.dumps(result))
        self.assertEqual(result[0]['spdisplays_vram'],'4 GB')

    def test_missing_or_unrecognized_fields_stay_unknown(self):
        result=inventory.gpu_rows(b'{"SPDisplaysDataType":[{"sppci_model":"Example","spdisplays_metal":true}]}')
        self.assertIsNone(result[0]['spdisplays_vram'])
        self.assertIsNone(result[0]['spdisplays_metal'])

    def test_nested_or_oversized_gpu_value_is_never_dumped(self):
        source={'SPDisplaysDataType':[{'sppci_model':{'private':'value'},'spdisplays_vram':'x'*257}]}
        self.assertTrue(all(v is None for v in inventory.gpu_rows(json.dumps(source).encode())[0].values()))

    def test_unknown_shape_or_oversized_response_is_refused(self):
        for value in (b'{}',b'[]',b'{"SPDisplaysDataType":[false]}',b'x'*(inventory.MAX_OUTPUT_BYTES+1)):
            with self.assertRaises(ValueError):inventory.gpu_rows(value)

    def test_one_bounded_read_no_model_request_or_installation(self):
        with patch.object(inventory.platform,'system',return_value='Darwin'),patch.object(inventory.platform,'machine',return_value='x86_64'),patch.object(inventory.platform,'mac_ver',return_value=('15.0','','')),patch.object(inventory.shutil,'which',return_value=None),patch.object(inventory.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'{"SPDisplaysDataType":[]}')) as call:
            result=inventory.collect()
        call.assert_called_once_with(['/usr/sbin/system_profiler','-json','SPDisplaysDataType'],capture_output=True,timeout=20,check=False)
        self.assertEqual(result['modelInferenceRequests'],0)
        self.assertEqual(result['compatibilityVerdict'],'not_determined')
        self.assertEqual(result['performanceVerdict'],'not_measured')
        self.assertFalse(result['productionModified'])

    def test_timeout_and_command_failure_do_not_retry(self):
        for failure,status in [(subprocess.TimeoutExpired('profiler',20),'timeout_no_retry'),(OSError('unavailable'),'unavailable_no_retry')]:
            with patch.object(inventory.platform,'system',return_value='Darwin'),patch.object(inventory.subprocess,'run',side_effect=failure) as call:
                result=inventory.collect()
            self.assertEqual(result['gpuReadStatus'],status);self.assertEqual(call.call_count,1)

    def test_non_macos_refuses_before_queries(self):
        with patch.object(inventory.platform,'system',return_value='Linux'),patch.object(inventory.subprocess,'run') as call:
            with self.assertRaisesRegex(ValueError,'macos_required'):inventory.collect()
        call.assert_not_called()


if __name__=='__main__':unittest.main()
