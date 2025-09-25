# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Documentation builder."""

import json
import os
import shutil
import subprocess

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GENERATED_FILENAME = 'v1/osv_service_v1.swagger.json'


def main():
  api_proto_dir = os.path.join(_ROOT_DIR, 'api', 'proto', 'osv', 'v1')
  googleapis_dir = os.path.join(_ROOT_DIR, 'third_party', 'googleapis')
  service_proto_path = os.path.join(api_proto_dir, 'osv_service_v1.proto')

  # Add OSV dependencies.
  osv_path = os.path.join(_ROOT_DIR, 'osv')

  subprocess.run([
      'protoc',
      '-I',
      _ROOT_DIR,
      '-I',
      googleapis_dir,
      '--openapiv2_out',
      '.',
      '--openapiv2_opt',
      'logtostderr=true',
      service_proto_path,
  ],
                 check=True)

  with open(_GENERATED_FILENAME) as f:
    spec = json.load(f)

  spec['host'] = 'api.osv.dev'
  spec['info']['title'] = 'OSV'
  spec['info']['version'] = '1.0'

  with open(_GENERATED_FILENAME, 'w') as f:
    f.write(json.dumps(spec, indent=2))

  shutil.move(_GENERATED_FILENAME, os.path.basename(_GENERATED_FILENAME))


if __name__ == '__main__':
  main()
