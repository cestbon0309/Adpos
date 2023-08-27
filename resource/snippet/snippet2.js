// 获取元素的绝对位置坐标（像对于页面左上角）
function getElementPagePosition(element){
    //计算x坐标
    var actualLeft = element.offsetLeft;
    var current = element.offsetParent;
    while (current !== null){
      actualLeft += current.offsetLeft;
      current = current.offsetParent;
    }
    //计算y坐标
    var actualTop = element.offsetTop;
    var current = element.offsetParent;
    while (current !== null){
      actualTop += (current.offsetTop+current.clientTop);
      current = current.offsetParent;
    }
    //返回结果
    return {x: actualLeft, y: actualTop}
  }
  
  elements = document.getElementsByTagName("img")
  for(let i=0; i<elements.length; i++)
    console.log(elements[i].src, getElementPagePosition(elements[i]));