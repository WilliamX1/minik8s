import React, { useContext , useState} from "react";
import {Actions, FlowContext} from "../../context";

export default function PopoverCard({ edge, source, target , content}) {
  // const [name, setName] = useLocalStorage(edge);
  const {
    state: { flowData }, dispatch
  } = useContext(FlowContext);

  const sourceNode = flowData.get(source);
  const targetNode = flowData.get(target);
  const trigger = (els) => {
    dispatch({
      type: Actions.TRIGGER,
      payload: a,
    });
  };
  let a = localStorage.getItem(edge);

  let inputChange=(event)=>{
    a = event.target.value;
  }

  let handleClick=(event)=>{
    localStorage.setItem(edge, a);
    console.log(localStorage.getItem(edge));
    trigger(a);
  }

  return (
      <>
        <div className="linkedge-card">
          <div className="linkedge-card-item">
            <div className="linkedge-card-item__title">{sourceNode?.label}</div>
            <div className="linkedge-card-item__tips">{sourceNode?.remark}</div>
          </div>
          <div className="linkedge-card-item__icon">-></div>
          <div className="linkedge-card-item">
            <div className="linkedge-card-item__title">{targetNode?.label}</div>
            <div className="linkedge-card-item__tips">{targetNode?.remark}</div>
          </div>
        </div><br/>
          <text>当前转移表达式：{a}</text><br/>
          <text>请输入分支表达式（默认为true, 即无条件转移）</text><br/>
          <input type="text" onChange={inputChange}/>
        <button onClick={handleClick}>提交</button>
      </>
  );
}
