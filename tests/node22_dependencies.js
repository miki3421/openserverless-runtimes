const assert = require('assert');
const crypto = require('node:crypto');
const query = require('query-string');
assert.equal(query.parse('q=hello%20world').q, 'hello world');
const AwsS3 = require('aws-s3');
const secret='synthetic-not-a-credential';
global.fetch = async (url, options) => {
  assert.equal(url, 'http://synthetic.invalid');
  const body=options.body;
  const date=body.get('X-Amz-Credential').split('/')[1];
  let key=crypto.createHmac('sha256','AWS4'+secret).update(date).digest();
  for(const v of ['us-east-1','s3','aws4_request'])key=crypto.createHmac('sha256',key).update(v).digest();
  const expected=crypto.createHmac('sha256',key).update(body.get('Policy')).digest('hex');
  assert.equal(body.get('X-Amz-Signature'),expected);
  return {ok:true,status:204};
};
const client=new AwsS3({bucketName:'synthetic',region:'us-east-1',accessKeyId:'synthetic',secretAccessKey:secret,s3Url:'http://synthetic.invalid'});
client.uploadFile(new Blob(['synthetic'],{type:'text/plain'}),'fixture').then(r=>{assert.equal(r.status,204);console.log('query decoding and AWS signing: PASS')}).catch(e=>{console.error(e);process.exit(1)});
