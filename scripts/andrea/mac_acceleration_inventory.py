"""Read GPU/OS build prerequisites without inference or installation.

Filters the display inventory to GPU fields only: no monitor serial numbers,
user paths, environment, vault, model files, downloads or service mutations.
Reported Metal support and VRAM are observations, not a compatibility verdict.
"""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys

MAX_OUTPUT_BYTES = 262144
GPU_FIELDS = ('sppci_model', 'sppci_vendor', 'spdisplays_vram', 'spdisplays_vram_shared',
              'spdisplays_metal', 'spdisplays_mtlgpufamily')


def gpu_rows(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_OUTPUT_BYTES:
        raise ValueError('gpu_inventory_too_large')
    value = json.loads(raw)
    devices = value.get('SPDisplaysDataType') if isinstance(value, dict) else None
    if not isinstance(devices, list) or len(devices) > 16:
        raise ValueError('gpu_inventory_shape_unknown')
    rows = []
    for item in devices:
        if not isinstance(item, dict):
            raise ValueError('gpu_inventory_shape_unknown')
        row = {key: item[key] if isinstance(item.get(key), str) and len(item[key]) <= 256 else None
               for key in GPU_FIELDS}
        rows.append(row)
    return rows


def collect():
    if platform.system() != 'Darwin':
        raise ValueError('macos_required')
    result = {'mode': 'read_only_mac_acceleration_inventory', 'architecture': platform.machine(),
              'macosVersion': platform.mac_ver()[0] or None,
              'gpuFieldsReported': None, 'gpuReadStatus': 'unknown',
              'commandsPresent': {name: shutil.which(name) is not None for name in ('git', 'cmake', 'clang')},
              'commandPresenceDoesNotProveBuildWorks': True,
              'compatibilityVerdict': 'not_determined', 'performanceVerdict': 'not_measured',
              'modelInferenceRequests': 0, 'automaticRetries': 0,
              'productionModified': False, 'existingProcessesTerminated': False}
    try:
        command = subprocess.run(['/usr/sbin/system_profiler', '-json', 'SPDisplaysDataType'],
                                 capture_output=True, timeout=20, check=False)
        if command.returncode != 0:
            raise ValueError('gpu_inventory_command_failed')
        result['gpuFieldsReported'] = gpu_rows(command.stdout)
        result['gpuReadStatus'] = 'read'
    except subprocess.TimeoutExpired:
        result['gpuReadStatus'] = 'timeout_no_retry'
    except (OSError, ValueError):
        result['gpuReadStatus'] = 'unavailable_no_retry'
    return result


def main():
    try:
        print(json.dumps(collect(), ensure_ascii=False, indent=2))
        return 0
    except ValueError as exc:
        print('Lettura fermata: '+str(exc)+'. Nessuna modifica.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
