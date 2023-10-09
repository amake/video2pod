import os
import boto3
from configparser import ConfigParser
from glob import glob
import subprocess


def load_config(config_file):
    if not os.path.isfile(config_file):
        print('No config file found. Please create one.')
        exit(1)
    c = ConfigParser()
    c.read(config_file)
    return c


config = load_config('config.ini')
deploy_bucket = config['deployment']['deploy_bucket']
deploy_key_prefix = config['deployment']['deploy_key_prefix']

s3 = boto3.client('s3')

mime_types = {
    '.txt': 'text/plain',
    '.xml': 'application/xml',
    '.mp3': 'audio/mpeg',
}


def run(event, context):
    os.makedirs('/tmp/archive', exist_ok=True)
    s3.download_file(
        deploy_bucket,
        f'{deploy_key_prefix}archive.txt',
        '/tmp/archive/archive.txt'
    )

    subprocess.run(['make', 'archive', 'PREFIX=/tmp',
                   'env=/var/lang'], check=True)
    subprocess.run(['make', 'all', 'PREFIX=/tmp',
                   'env=/var/lang'], check=True)

    # We would have just run `make deploy` but for some reason the invocation
    # fails when executing on AWS Lambda only with:
    #
    #   awscliv2 - ERROR - Command failed with code 127
    #
    # So reimplement in Python

    # subprocess.run(['make', 'deploy', 'PREFIX=/tmp',
    #                 'env=/var/lang', 'dryrun='], check=True)

    for f in glob('/tmp/dist/*'):
        _, ext = os.path.splitext(f)
        if ext not in mime_types:
            raise ValueError(f'Unknown file extension {ext}')
        extra_args = {
            'ACL': 'public-read',
            'ContentType': mime_types[ext],
        }
        if not f.endswith('.mp3'):
            extra_args['CacheControl'] = 'max-age=30'
        key = f'{deploy_key_prefix}{os.path.basename(f)}'
        print(f'Uploading {f} to s3://{deploy_bucket}/{key}')
        s3.upload_file(f, deploy_bucket, key, ExtraArgs=extra_args)
