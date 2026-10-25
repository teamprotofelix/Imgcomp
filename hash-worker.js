import {hashBlob} from './sha256.js';
self.onmessage=async({data:{id,file}})=>{try{const digest=await hashBlob(file,()=>{},bytes=>self.postMessage({id,bytes}));self.postMessage({id,digest});}catch(e){self.postMessage({id,error:e.message});}};
