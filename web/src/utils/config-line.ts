/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-18 09:41:52
 * @LastEditors: htang
 * @LastEditTime: 2023-09-18 09:54:35
 */
export const CONFIG_LINE_DASH = [{
  node: `<svg xmlns="http://www.w3.org/2000/svg" version="1.1" style="height: 20px;">
    <g fill="none" stroke="black" stroke-width="1">
      <path d="M0 9 l85 0"></path>
    </g>
  </svg>`,
  value: '[]',
}, {
  node: `<svg xmlns="http://www.w3.org/2000/svg" version="1.1" style="height: 20px;">
    <g fill="none" stroke="black" stroke-width="1">
      <path stroke-dasharray="5 5" d="M0 9 l85 0"></path>
    </g>
  </svg>`,
  value: '[5, 5]'
}, {
  node: `<svg xmlns="http://www.w3.org/2000/svg" version="1.1" style="height: 20px">
    <g fill="none" stroke="black" stroke-width="1">
      <path stroke-dasharray="10 10" d="M0 9 l85 0"></path>
    </g>
  </svg>`,
  value: '[10, 10]'
}, {
  node: `<svg xmlns="http://www.w3.org/2000/svg" version="1.1" style="height: 20px;">
    <g fill="none" stroke="black" stroke-width="1">
      <path stroke-dasharray="10 10 2 10" d="M0 9 l85 0"></path>
    </g>
  </svg>`,
  value: '[10, 10, 2, 10]'
}]