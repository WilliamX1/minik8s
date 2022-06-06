import React, { useContext } from "react";
import classnames from "classnames";
import { FlowContext } from "../context";

function replacer(key, value) {
  if(value instanceof Map) {
    return {
      dataType: 'Map',
      value: Array.from(value.entries()), // or with spread: value: [...value]
    };
  } else {
    return value;
  }
}

function reviver(key, value) {
  if(typeof value === 'object' && value !== null) {
    if (value.dataType === 'Map') {
      return new Map(value.value);
    }
  }
  return value;
}

export default function Toolbar() {
  const { state, dispatch } = useContext(FlowContext);
  // const {
  //   state: { reactFlowInstance, flowData},
  // } = useContext(FlowContext);

  // 保存
  let api_server_path = 'http://192.168.1.12:5050'

  const handleSave = () => {
    let elements = JSON.stringify(state.reactFlowInstance.toObject()['elements']);
    let local_stroage = JSON.stringify(localStorage);
    let flow_data = JSON.stringify(state.flowData, replacer);
    let dag_name = localStorage.getItem("DAG_name");
    console.log(state.flowData);
    console.log('elements', elements);
    console.log('edge_type = ', local_stroage);
    console.log('flow_data = ', flow_data);
    fetch(api_server_path + '/DAG/' + dag_name + '/upload',{
      method:'post',
      headers:{
        'Accept':'application/json,text/plain,*/*',/* 格式限制：json、文本、其他格式 */
        'Content-Type':'application/x-www-form-urlencoded'/* 请求内容类型 */
      },
      body:`elements=${elements}&localStorage=${local_stroage}&flowData=${flow_data}`
    }).then((response)=>{
      return response.json()
    }).then((data)=>{
      console.log(data)
    }).catch(function(error){
      console.log(error)
    })
  };

  // 重置节点
  // const handleRest = () => {};

  let inputChange=(event)=>{
    localStorage.setItem('DAG_name', event.target.value);
    console.log(localStorage.getItem('DAG_name'));
  }

  return (
    <div className="toolbar">
      {/* <button className={classnames(["button"])} onClick={handleRest}>
        重置
      </button> */}
      <input type='text' onChange={inputChange} defaultValue='DAG_name'></input>
      <button className={classnames(["button", "primary-btn"])} onClick={handleSave}>
        保存
      </button>
    </div>
  );
}
