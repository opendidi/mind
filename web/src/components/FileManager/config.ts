/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2025-06-13 14:32:10
 * @LastEditors: htang
 * @LastEditTime: 2025-08-19 10:37:43
 */
import ai from "@/assets/images/file-explorer/ai.svg";
import avi from "@/assets/images/file-explorer/avi.svg";
import css from "@/assets/images/file-explorer/css.svg";
import csv from "@/assets/images/file-explorer/csv.svg";
import dbf from "@/assets/images/file-explorer/dbf.svg";
import dir from "@/assets/images/file-explorer/dir.svg";
import doc from "@/assets/images/file-explorer/doc.svg";
import dwg from "@/assets/images/file-explorer/dwg.svg";
import exe from "@/assets/images/file-explorer/exe.svg";
import file from "@/assets/images/file-explorer/file.svg";
import fla from "@/assets/images/file-explorer/fla.svg";
import flash from "@/assets/images/file-explorer/flash.svg";
import folder from "@/assets/images/file-explorer/folder.svg";
import folderfull from "@/assets/images/file-explorer/folderfull.svg";
import folderopen from "@/assets/images/file-explorer/folderopen.svg";
import gif from "@/assets/images/file-explorer/gif.svg";
import html from "@/assets/images/file-explorer/html.svg";
import iso from "@/assets/images/file-explorer/iso.svg";
import javascript from "@/assets/images/file-explorer/javascript.svg";
import jpg from "@/assets/images/file-explorer/jpg.svg";
import jsonFile from "@/assets/images/file-explorer/json-file.svg";
import mp3 from "@/assets/images/file-explorer/mp3.svg";
import mp4 from "@/assets/images/file-explorer/mp4.svg";
import pdf from "@/assets/images/file-explorer/pdf.svg";
import png from "@/assets/images/file-explorer/png.svg";
import ppt from "@/assets/images/file-explorer/ppt.svg";
import psd from "@/assets/images/file-explorer/psd.svg";
import rtf from "@/assets/images/file-explorer/rtf.svg";
import search from "@/assets/images/file-explorer/search.svg";
import svg from "@/assets/images/file-explorer/svg.svg";
import trash from "@/assets/images/file-explorer/trash.svg";
import trashbox from "@/assets/images/file-explorer/trashbox.svg";
import txt from "@/assets/images/file-explorer/txt.svg";
import xls from "@/assets/images/file-explorer/xls.svg";
import xml from "@/assets/images/file-explorer/xml.svg";
import zip1 from "@/assets/images/file-explorer/zip-1.svg";
import zip from "@/assets/images/file-explorer/zip.svg";

const fileIconMap: any = {
  'ai': ai,
  'dir': dir,
  'mp3': mp3,
  'mp4': mp4,
  'png': png,
  'jpg': jpg,
  'jpeg': jpg,
  'gif': gif,
  'txt': txt,
  'doc': doc,
  'docx': doc,
  'avi': avi,
  'css': css,
  'csv': csv,
  'dbf': dbf,
  'dwg': dwg,
  'exe': exe,
  'fla': fla,
  'flash': flash,
  'html': html,
  'iso': iso,
  'javascript': javascript,
  'json': jsonFile,
  'pdf': pdf,
  'ppt': ppt,
  'psd': psd,
  'rtf': rtf,
  'svg': svg,
  'xls': xls,
  'xml': xml,
  'zip': zip,
  'file': file,
  'folder': folder,
  'folderfull': folderfull,
  'folderopen': folderopen,
  'search': search,
  'trash': trash,
  'trashbox': trashbox
};

/**
 * 根据文件扩展名返回对应的图标
 */
const getFileIconByExt = (ext: string) => {
  console.log(fileIconMap[ext], ext)
  return fileIconMap[ext] ? `url(${fileIconMap[ext]})` : '';
};

export {
  getFileIconByExt
}