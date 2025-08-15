/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2025-04-25 14:49:08
 * @LastEditors: htang
 * @LastEditTime: 2025-04-25 15:52:24
 */

export const FileExplorer = function (options: any) {
  this._filterExt = {
    // all: ['.gif', '.jpg', '.png', '.bmp', '.jpeg', '.swf', '.mp3', '.mp4', '.flv', '.webm', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf', '.odt', '.csv', '.rar', '.zip'],
    all: ['.gif', '.jpg', '.png', '.bmp', '.jpeg', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf', '.odt', '.csv'],
    image: ['.gif', '.jpg', '.png', '.bmp', '.jpeg'],
    // flash: ['.swf'],
    audio: ['.mp3', '.wma', '.ra'],
    video: ['.mp4', '.flv', '.webm'],
    doc: ['.txt', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf', '.odt', '.csv'],
    // rar: ['.rar', '.zip'],
    // material lib
    // material: ['.gif', '.jpg', '.png', '.bmp', '.jpeg', '.mp3', '.wma', '.ra']
    material: ['.gif', '.jpg', '.png', '.bmp', '.jpeg'],
    // svg
    icons: ['.svg']
  }
}
