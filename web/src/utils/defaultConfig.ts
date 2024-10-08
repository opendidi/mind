/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-11-28 09:57:30
 * @LastEditors: htang
 * @LastEditTime: 2023-11-28 19:42:43
 */
export const animateType = [{
  name: '上下跳动',
  key: 'upDown',
  frames: [{
    duration: 100,
    y: -10
  }, {
    duration: 80,
    y: 10
  }, {
    duration: 50,
    y: -10
  }, {
    duration: 30,
    y: 10
  }, {
    duration: 300,
    y: 0
  }]
}, {
  name: '左右跳动',
  key: 'leftRight',
  frames: [{
    duration: 100,
    x: -10
  }, {
    duration: 80,
    x: 10
  }, {
    duration: 50,
    x: -10
  }, {
    duration: 30,
    x: 10
  }, {
    duration: 300,
    x: 0
  }]
}, {
  name: '心跳',
  key: 'heart',
  frames: [{
    duration: 100,
    scale: 1.1
  }, {
    duration: 400,
    scale: 1
  }],
}, {
  name: '成功',
  key: 'success',
  frames: [{
    background: "#389e0d22",
    color: "#237804",
    duration: 500
  }],
}, {
  name: '警告',
  key: 'warning',
  frames: [{
    color: "#fa8c16",
    duration: 300,
    lineDash: [10, 10]
  }, {
    color: "#fa8c16",
    duration: 500
  }, {
    color: "#fa8c16",
    duration: 300,
    lineDash: [10, 10]
  }],
}, {
  name: '错误',
  key: 'error',
  frames: [{
    background: "#cf132222",
    color: "#cf1322",
    duration: 100
  }],
}, {
  name: '炫耀',
  key: 'show',
  frames: [{
    color: "#fa541c",
    duration: 100,
    rotate: -10
  }, {
    color: "#fa541c",
    duration: 100,
    rotate: 10
  }, {
    color: "#fa541c",
    duration: 100,
    rotate: 0
  }],
}, {
  name: "跳动",
  key: "bounce",
  frames: [{
    duration: 300,
    y: 10
  }]
}, {
  name: "旋转",
  key: "rotate",
  frames: [{
    duration: 1000,
    rotate: 360
  }]
}, {
  name: "提示",
  key: "tip",
  frames: [{
    duration: 300,
    scale: 1.3
  }]
}, {
  name: '自定义',
  key: 'custom',
  frames: [],
}]

export const fontFamilys = [{
  name: 'serif',
  value: 'serif',
}, {
  name: 'sans-serif',
  value: 'sans-serif',
}, {
  name: 'monospace',
  value: 'monospace',
}, {
  name: 'cursive',
  value: 'cursive',
}, {
  name: 'fantasy',
  value: 'fantasy',
}, {
  name: 'system-ui',
  value: 'system-ui',
}, {
  name: 'emoji',
  value: 'emoji',
}, {
  name: 'math',
  value: 'math',
}, {
  name: 'fangsong',
  value: 'fangsong',
}, {
  name: '宋体',
  value: '宋体',
}, {
  name: '微软雅黑',
  value: '微软雅黑',
}, {
  name: '黑体',
  value: '黑体',
}, {
  name: '楷体',
  value: '楷体',
}]