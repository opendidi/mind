/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2023-09-14 08:50:34
 * @LastEditors: htang
 * @LastEditTime: 2024-04-10 10:35:05
 */
import moment from 'moment'

const KEY: string = 'meta2d-graphic-groups';

export const GRAPHIC_GROUPS = [{
  name: '基本形状',
  show: true,
  list: [{
    name: '正方形',
    icon: 'l-rect',
    id: 1,
    data: {
      width: 100,
      height: 100,
      name: 'square',
    },
  }, {
    name: '矩形',
    icon: 'l-rectangle',
    id: 2,
    data: {
      width: 200,
      height: 50,
      borderRadius: 0.1,
      name: 'rectangle',
    },
  }, {
    name: '圆',
    icon: 'l-circle',
    id: 3,
    data: {
      width: 100,
      height: 100,
      name: 'circle',
    },
  }, {
    name: '三角形',
    icon: 'l-triangle',
    id: 4,
    data: {
      width: 100,
      height: 100,
      name: 'triangle',
    },
  }, {
    name: '菱形',
    icon: 'l-diamond',
    id: 5,
    data: {
      width: 100,
      height: 100,
      name: 'diamond',
    },
  }, {
    name: '五边形',
    icon: 'l-pentagon',
    id: 6,
    data: {
      width: 100,
      height: 100,
      name: 'pentagon',
    },
  }, {
    name: '六边形',
    icon: 'l-hexagon',
    id: 7,
    data: {
      width: 100,
      height: 100,
      name: 'hexagon',
    },
  }, {
    name: '五角星',
    icon: 'l-pentagram',
    id: 8,
    data: {
      width: 100,
      height: 100,
      name: 'pentagram',
    },
  }, {
    name: '左箭头',
    icon: 'l-arrow-left',
    id: 9,
    data: {
      width: 120,
      height: 60,
      name: 'leftArrow',
    },
  }, {
    name: '右箭头',
    icon: 'l-arrow-right',
    id: 10,
    data: {
      width: 120,
      height: 60,
      name: 'rightArrow',
    },
  }, {
    name: '双向箭头',
    icon: 'l-twoway-arrow',
    id: 11,
    data: {
      width: 150,
      height: 60,
      name: 'twowayArrow',
    },
  }, {
    name: '云',
    icon: 'l-cloud',
    id: 13,
    data: {
      width: 100,
      height: 100,
      name: 'cloud',
    },
  }, {
    name: '消息框',
    icon: 'l-msg',
    id: 14,
    data: {
      textTop: -0.1,
      width: 100,
      height: 100,
      name: 'message',
    },
  }, {
    name: '文件',
    icon: 'l-file',
    id: 15,
    data: {
      width: 80,
      height: 100,
      name: 'file',
    },
  }, {
    name: '图片',
    icon: 'l-image',
    id: 15,
    data: {
      width: 100,
      height: 100,
      name: 'image',
      image: "https://assets.le5lecdn.com/2d/img/logo.png"
    },
  }, {
    name: '视频',
    icon: 'video-camera',
    data: {
      name: 'video',
      width: 100,
      height: 100,
      video: 'https://video.699pic.com/videos/17/69/11/a_aa3jeKZ0D63g1556176911_10s.mp4',
      autoPlay: true,
    },
  }, {
    name: '立方体',
    icon: 'l-cube',
    id: 18,
    data: {
      width: 60,
      height: 100,
      name: 'cube',
      z: 0.25,
      props: {
        custom: [{
          key: 'z',
          label: 'Z',
          type: 'number',
          min: 0,
          placeholder: '<= 1 即宽度的比例',
        }, {
          key: 'backgroundFront',
          label: '前背景色',
          type: 'color',
        }, {
          key: 'backgroundUp',
          label: '顶背景色',
          type: 'color',
        }, {
          key: 'backgroundRight',
          label: '右背景色',
          type: 'color',
        }],
      },
    },
  }, {
    name: '人',
    icon: 'l-people',
    id: 19,
    data: {
      width: 70,
      height: 100,
      name: 'people',
    },
  }],
}, {
  name: '表单',
  show: true,
  list: [{
    name: '按钮',
    icon: 'iconfont icon-buy-button',
    data: {
      name: "rectangle",
      width: 80,
      height: 30,
      borderRadius: 0.2,
      text: "按钮",
      background: "#1890ff",
      color: "#1890ff",
      textColor: "#fff",
      activeBackground: "#40a9ff", //选中
      activeColor: "#40a9ff",
      activeTextColor: "#fff",
      hoverBackground: "#40a9ff", //鼠标经过
      hoverColor: "#40a9ff",
      hoverTextColor: "#fff",
    },
    events: [
      // {
      //   name: "click",
      //   // 执行动作
      //   action: eventAction.Link,
      //   // 触发条件
      //   where: {
      //     type: 'comparison',
      //     key: "text",
      //     comparison: "==",
      //     value: "矩形"
      //   },
      //   value: "",
      // }
    ],
  }, {
    name: '开关',
    icon: 'iconfont icon-switchButton',
    data: {
      name: 'switch',
      height: 30,
      width: 60,
      checked: false,
      offColor: "#BFBFBF",
      onColor: "#1890ff",
      disableOffColor: "#E5E5E5",
      disableOnColor: "#A3D3FF",
      locked: 0,
      //disable: true,
    },
    events: []
  }, {
    // https://doc.le5le.com/document/119756343#radio%20%E5%8D%95%E9%80%89%E6%A1%86
    name: '单选框',
    icon: 'iconfont icon-danxuanzu',
    data: {
      name: 'radio',
      width: 150,
      height: 100,
      direction: "vertical",
      checked: '',
      options: [
        { text: "选项一" },
        { text: "选项二" },
        { text: "选项三", isForbidden: true },
      ],
    },
    events: []
  }, {
    name: '多选框',
    icon: 'iconfont icon-md-checkbox-outline',
    data: {
      name: "checkbox",
      width: 30,
      height: 30,
      checked: true,
      // isForbidden: true,
      value: '选项一',
    }
  }, {
    name: '滑动输入条',
    icon: 'iconfont icon-sliders-h',
    data: {
      name: "slider",
      width: 300,
      height: 30,
      value: 10,
      textWidth: 50,
      barHeight: 4,
      min: 0,
      max: 100,
      color: "#1890ff",
      background: "#D4D6D9",
      textColor: "#222",
      unit: "%",
    }
  }, {
    name: '输入框',
    icon: 'iconfont icon-keshihuapingtaiicon_shurukuang',
    data: {
      name: "rectangle",
      height: 50,
      width: 200,
      input: true,
      borderRadius: 0.05,
      ellipsis: true,
      text: "输入数据",
      textAlign: "left",
      color: "#D9D9D9FF",
      textColor: "#000000FF",
      hoverTextColor: "#000000FF",
      activeTextColor: "#000000FF",
      textLeft: 10,
    }
  }, {
    name: '选择器',
    icon: 'iconfont icon-xuanzeqi',
    data: {
      name: "rectangle",
      height: 50,
      width: 200,
      borderRadius: 0.05,
      ellipsis: true,
      text: "选项1",
      textAlign: "left",
      color: "#D9D9D9FF",
      textColor: "#000000FF",
      hoverTextColor: "#000000FF",
      activeTextColor: "#000000FF",
      textLeft: 10,
      title: '下拉列表',
      dropdownList: [{
        text: "选项1",
      }, {
        text: "选项2"
      }, {
        text: "选项3"
      }],
    }
  }, {
    name: '时间',
    icon: 'iconfont icon-shangpaishijian',
    data: {
      name: 'time',
      width: 300,
      height: 40,
      text: `${moment().format('YYYY-MM-DD HH:mm:ss')}`,
      lineWidth: 0,
      // 绘画帧时长
      interval: 67,
      fillZero: true,
      form: [{
        key: 'timeFormat',
        name: '显示格式',
        type: 'text',
      }, {
        key: 'fillZero',
        name: '是否补0',
        type: 'switch',
      }],
      timeFormat: "`${year}-${month}-${day} ${hours}:${minutes}:${seconds} 星期${week}`",
    },
    events: []
  }]
}, {
  name: '2.5D-光伏系统',
  show: true,
  list: []
}, {
  name: '2.5D-制冷站',
  show: true,
  list: []
}, {
  name: '2.5D-废水处理',
  show: true,
  list: []
}, {
  name: '2.5D-废气治理',
  show: true,
  list: []
}, {
  name: '2.5D-火力发电',
  show: true,
  list: []
}, {
  name: '2.5D-智慧城市',
  show: true,
  list: []
}, {
  name: '2.5D-风力发电',
  show: true,
  list: []
}, {
  name: '2.5D-锅炉房',
  show: true,
  list: []
}, {
  name: '太阳能光伏发电',
  show: true,
  list: []
}, {
  name: 'IoT-MNMS-移动网管域',
  show: true,
  list: []
}, {
  name: 'IoT-SAFETY(安全)',
  show: true,
  list: []
}, {
  name: '流程图',
  show: true,
  list: [{
    name: '开始/结束',
    icon: 'l-flow-start',
    id: 21,
    data: {
      text: '开始/结束',
      width: 120,
      height: 40,
      borderRadius: 0.5,
      name: 'rectangle',
    },
  }, {
    name: '流程',
    icon: 'l-rectangle',
    id: 22,
    data: {
      text: '流程',
      width: 120,
      height: 40,
      name: 'rectangle',
    },
  }, {
    name: '判定',
    icon: 'l-diamond',
    id: 23,
    data: {
      text: '判定',
      width: 120,
      height: 60,
      name: 'diamond',
    },
  }, {
    name: '数据',
    icon: 'l-flow-data',
    id: 24,
    data: {
      text: '数据',
      width: 120,
      height: 50,
      name: 'flowData',
      offsetX: 0.14,
    },
  }, {
    name: '准备',
    icon: 'l-flow-ready',
    id: 25,
    data: {
      text: '准备',
      width: 120,
      height: 50,
      name: 'hexagon',
    },
  }, {
    name: '子流程',
    icon: 'l-flow-subprocess',
    id: 26,
    data: {
      text: '子流程',
      width: 120,
      height: 50,
      name: 'flowSubprocess',
    },
  }, {
    name: '数据库',
    icon: 'l-db',
    id: 27,
    data: {
      text: '数据库',
      width: 80,
      height: 120,
      name: 'flowDb',
    },
  }, {
    name: '文档',
    icon: 'l-flow-document',
    id: 28,
    data: {
      text: '文档',
      width: 120,
      height: 100,
      name: 'flowDocument',
    },
  }, {
    name: '内部存储',
    icon: 'l-internal-storage',
    id: 29,
    data: {
      text: '内部存储',
      width: 120,
      height: 80,
      name: 'flowInternalStorage',
    },
  }, {
    name: '外部存储',
    icon: 'l-extern-storage',
    id: 30,
    data: {
      text: '外部存储',
      width: 120,
      height: 80,
      name: 'flowExternStorage',
    },
  }, {
    name: '队列',
    icon: 'l-flow-queue',
    id: 31,
    data: {
      text: '队列',
      width: 100,
      height: 100,
      name: 'flowQueue',
    },
  }, {
    name: '手动输入',
    icon: 'l-flow-manually',
    id: 32,
    data: {
      text: '手动输入',
      width: 120,
      height: 80,
      name: 'flowManually',
    },
  }, {
    name: '展示',
    icon: 'l-flow-display',
    id: 33,
    data: {
      text: '展示',
      width: 120,
      height: 80,
      name: 'flowDisplay',
    },
  }, {
    name: '并行模式',
    icon: 'l-flow-parallel',
    id: 34,
    data: {
      text: '并行模式',
      width: 120,
      height: 50,
      name: 'flowParallel',
    },
  }, {
    name: '注释',
    icon: 'l-flow-comment',
    id: 35,
    data: {
      text: '注释',
      width: 100,
      height: 100,
      name: 'flowComment',
    },
  }],
}, {
  name: '活动图',
  show: true,
  list: [{
    name: '开始',
    icon: 'l-inital',
    id: 36,
    data: {
      text: '',
      width: 30,
      height: 30,
      name: 'circle',
      background: '#555',
      lineWidth: 0,
    },
  }, {
    name: '结束',
    icon: 'l-final',
    id: 37,
    data: {
      width: 30,
      height: 30,
      name: 'activityFinal',
    },
  }, {
    name: '活动',
    icon: 'l-action',
    id: 38,
    data: {
      text: '活动',
      width: 120,
      height: 50,
      borderRadius: 0.25,
      name: 'rectangle',
    },
  }, {
    name: '决策/合并',
    icon: 'l-diamond',
    id: 39,
    data: {
      text: '决策/合并',
      width: 120,
      height: 50,
      name: 'diamond',
    },
  }, {
    name: '垂直泳道',
    icon: 'l-swimlane-v',
    id: 40,
    data: {
      text: '垂直泳道',
      width: 200,
      height: 500,
      name: 'swimlaneV',
      textBaseline: 'top',
      textTop: 20,
      // textHeight: ,
      lineTop: 0.08,
    },
  }, {
    name: '水平泳道',
    icon: 'l-swimlane-h',
    id: 41,
    data: {
      text: '水平泳道',
      width: 500,
      height: 200,
      name: 'swimlaneH',
      textWidth: 0.01,
      textLeft: 0.04,
      textAlign: 'left',
      lineLeft: 0.08,
    },
  }, {
    name: '垂直分岔/汇合',
    icon: 'l-fork-v',
    id: 42,
    data: {
      text: '垂直分岔/汇合',
      width: 10,
      height: 150,
      name: 'forkV',
      fillStyle: '#555',
      strokeStyle: 'transparent',
    },
  }, {
    name: '水平分岔/汇合',
    icon: 'l-fork',
    id: 43,
    data: {
      text: '水平分岔/汇合',
      width: 150,
      height: 10,
      name: 'forkH',
      fillStyle: '#555',
      strokeStyle: 'transparent',
    },
  }],
}, {
  name: '时序图和类图',
  show: true,
  list: [
    {
      name: '生命线',
      icon: 'l-lifeline',
      id: 44,
      data: {
        text: '生命线',
        width: 150,
        height: 400,
        textHeight: 50,
        name: 'lifeline',
      },
    }, {
      name: '激活',
      icon: 'l-focus',
      id: 45,
      data: {
        text: '激活',
        width: 12,
        height: 200,
        name: 'sequenceFocus',
      },
    }, {
      name: '简单类',
      icon: 'l-simple-class',
      id: 46,
      data: {
        text: 'Topolgoy',
        width: 270,
        height: 200,
        textHeight: 200,
        name: 'simpleClass',
        textAlign: 'center',
        textBaseline: 'top',
        textTop: 10,
        list: [{
          text: '- name: string\n+ setName(name: string): void',
        }],
      },
    }, {
      name: '类',
      icon: 'l-class',
      id: 47,
      data: {
        text: 'Topolgoy',
        width: 270,
        height: 200,
        textHeight: 200,
        name: 'interfaceClass',
        textAlign: 'center',
        textBaseline: 'top',
        textTop: 10,
        list: [{
          text: '- name: string',
        }, {
          text: '+ setName(name: string): void',
        }],
      },
    },
  ],
}, {
  name: '故障树',
  show: true,
  list: [
    {
      name: '与门',
      icon: 'l-ANDmen',
      data: {
        name: 'andGate',
        width: 100,
        height: 150,
      },
    }, {
      name: '基本事件',
      icon: 'l-jibenshijian',
      data: {
        name: 'basicEvent',
        width: 100,
        height: 150,
      },
    }, {
      name: '未展开事件',
      icon: 'l-weizhankaishijian',
      data: {
        name: 'unexpandedEvent',
        width: 100,
        height: 150,
      },
    }, {
      name: '优先AND门',
      icon: 'l-youxianANDmen',
      data: {
        name: 'priorityAndGate',
        width: 100,
        height: 150,
      },
    }, {
      name: '禁止门',
      icon: 'l-jinzhimen',
      data: {
        name: 'forbiddenGate',
        width: 100,
        height: 150,
      },
    }, {
      name: '事件',
      icon: 'l-shijian',
      data: {
        name: 'event',
        width: 100,
        height: 150,
      },
    }, {
      name: '开关事件',
      icon: 'l-kaiguanshijian',
      data: {
        name: 'switchEvent',
        width: 100,
        height: 150,
      },
    }, {
      name: '条件事件',
      icon: 'l-tiaojianshijian',
      data: {
        name: 'conditionalEvent',
        width: 150,
        height: 100,
      },
    }, {
      name: '转移符号',
      icon: 'l-zhuanyifuhao',
      data: {
        name: 'transferSymbol',
        width: 100,
        height: 150,
      },
    }, {
      name: '或门',
      icon: 'l-ORmen',
      data: {
        name: 'orGate',
        width: 100,
        height: 150,
      },
    }, {
      name: '异或门',
      icon: 'l-yihuomen',
      data: {
        name: 'xorGate',
        width: 100,
        height: 150,
      },
    }, {
      name: '表决门',
      icon: 'l-biaojuemen',
      data: {
        name: 'votingGate',
        width: 100,
        height: 150,
      },
    },
  ],
}, {
  name: '脑图',
  show: true,
  list: [{
    name: '主题',
    icon: 'l-zhuti',
    data: {
      text: '主题',
      width: 200,
      height: 50,
      name: 'mindNode',
      borderRadius: 0.5,
    },
  }, {
    name: '子主题',
    icon: 'l-zizhuti',
    data: {
      text: '子主题',
      width: 160,
      height: 40,
      name: 'mindLine',
    },
  }],
}]

function commonImportFile(path: string, index: number) {
  const regex = /\.(svg|gif)/g;
  let suffix = path.substring(path.lastIndexOf(".") + 1)
  let _ = path.replace(regex, '').split('/');
  GRAPHIC_GROUPS[index].list.push({
    name: path.replace(regex, ''),
    icon: '',
    data: {
      name: suffix == 'svg' ? 'rectangle' : "gif",
      width: 101,
      height: 101,
      imageRatio: true,
      image: new URL(path, import.meta.url).href,
      label: decodeURIComponent(_[_.length - 1].split('-')[0]).trim(),
      lineWidth: 0
    },
  })
}

function getFileName(keys: string) {
  let array = keys.split('/')
  return array[array.length - 1];
}

// 获取图片url
export default async function GET_IMAGE_PATH(mkdir: string, name: string) {
  return await new URL(`/src/assets/images/${mkdir}/${name}`, import.meta.url).href;
};

function importFile() {
  let array = [{
    import: import.meta.glob(`@/assets/images/2.5D-光伏系统/*`),
    mkdir: '2.5D-光伏系统',
    index: 2,
  }, {
    import: import.meta.glob(`@/assets/images/2.5D-制冷站/*`),
    mkdir: '2.5D-制冷站',
    index: 3,
  }, {
    import: import.meta.glob(`@/assets/images/2.5D-废水处理/*`),
    mkdir: '2.5D-废水处理',
    index: 4,
  }, {
    import: import.meta.glob(`@/assets/images/2.5D-废气治理/*`),
    mkdir: '2.5D-废气治理',
    index: 5,
  }, {
    import: import.meta.glob(`@/assets/images/2.5D-火力发电/*`),
    mkdir: '2.5D-火力发电',
    index: 6,
  }, {
    import: import.meta.glob(`@/assets/images/2.5D-智慧城市/*`),
    mkdir: '2.5D-智慧城市',
    index: 7,
  }, {
    import: import.meta.glob(`@/assets/images/2.5D-风力发电/*`),
    mkdir: '2.5D-风力发电',
    index: 8,
  }, {
    import: import.meta.glob(`@/assets/images/2.5D-锅炉房/*`),
    mkdir: '2.5D-锅炉房',
    index: 9,
  }, {
    import: import.meta.glob(`@/assets/images/太阳能光伏发电/*`),
    mkdir: '太阳能光伏发电',
    index: 10,
  }, {
    import: import.meta.glob(`@/assets/images/IoT-MNMS-移动网管域/*`),
    mkdir: 'IoT-MNMS-移动网管域',
    index: 11,
  }, {
    import: import.meta.glob(`@/assets/images/IoT-SAFETY-安全/*`),
    mkdir: 'IoT-SAFETY-安全',
    index: 12,
  }];
  array.map((item) => {
    const modules = item.import;
    Object.keys(modules).forEach((key: string) => {
      const NEW_KEY: any = getFileName(key);
      if (NEW_KEY.indexOf('svg') !== -1) {
        modules[NEW_KEY] = GET_IMAGE_PATH(item.mkdir, NEW_KEY);
        delete modules[key];
        modules[NEW_KEY].then((path) => {
          commonImportFile(path, item.index);
        })
      }
    })
  })
  if (Object.keys(getGraphicGroups()).length == 0) {
    let obj = {};
    GRAPHIC_GROUPS.map((_: any) => {
      obj[_.name] = _.show;
    });
    setGraphicGroups(obj);
  }
}

importFile();

export function getGraphicGroups() {
  let data: any = localStorage.getItem(KEY);
  if (data) {
    return JSON.parse(data);
  } else {
    return {}
  }
}

export function setGraphicGroups(data: any) {
  return localStorage.setItem(KEY, JSON.stringify(data))
}

export function removeGraphicGroups() {
  return localStorage.removeItem(KEY)
}