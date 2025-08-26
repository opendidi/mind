/*
 * @Descripttion:
 * @version: 1.0.0
 * @Author: htang
 * @Date: 2025-08-26 14:35:49
 * @LastEditors: htang
 * @LastEditTime: 2025-08-26 14:49:31
 */
export class UrlParamsManager {
  // 获取hash部分的参数
  private static getHashParams(): URLSearchParams {
    const hash = window.location.hash;
    if (hash.includes('?')) {
      const queryString = hash.split('?')[1];
      return new URLSearchParams(queryString);
    }
    return new URLSearchParams();
  }

  // 更新hash部分的URL
  private static updateHashUrl(params: URLSearchParams, hashPath: string = ''): void {
    const baseHash = hashPath ? `#/${hashPath.replace(/^\/|\/$/g, '')}` : window.location.hash.split('?')[0];
    const newHash = params.toString() ? `${baseHash}?${params.toString()}` : baseHash;

    window.history.replaceState({}, '', newHash);
  }

  // 获取当前所有hash参数
  static getParams(): Record<string, string> {
    const params: Record<string, string> = {};
    const hashParams = this.getHashParams();

    for (const [key, value] of hashParams.entries()) {
      params[key] = value;
    }

    return params;
  }

  // 获取单个hash参数
  static getParam(key: string): string | null {
    const hashParams = this.getHashParams();
    return hashParams.get(key);
  }

  // 设置单个hash参数
  static setParam(key: string, value: string, hashPath?: string): Record<string, string> {
    const hashParams = this.getHashParams();
    hashParams.set(key, value);
    this.updateHashUrl(hashParams, hashPath);
    return this.getParams();
  }

  // 设置多个hash参数
  static setParams(params: Record<string, string>, hashPath?: string): Record<string, string> {
    const hashParams = this.getHashParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        hashParams.set(key, value);
      }
    });

    this.updateHashUrl(hashParams, hashPath);
    return this.getParams();
  }

  // 删除hash参数
  static removeParam(key: string, hashPath?: string): Record<string, string> {
    const hashParams = this.getHashParams();
    hashParams.delete(key);
    this.updateHashUrl(hashParams, hashPath);
    return this.getParams();
  }

  // 清空所有hash参数
  static clearParams(hashPath?: string): Record<string, string> {
    const baseHash = window.location.hash.split('?')[0];
    const newHash = hashPath ? `#/${hashPath.replace(/^\/|\/$/g, '')}` : baseHash;
    window.history.replaceState({}, '', newHash);
    return {};
  }

  // 自动附加域名参数到hash
  static autoAttachDomainParam(paramName: string = 'source'): Record<string, string> {
    const domain = window.location.hostname;
    return this.setParam(paramName, domain);
  }

  // 获取当前hash路径（不包含参数）
  static getHashPath(): string {
    const hash = window.location.hash;
    return hash.split('?')[0].replace(/^#\/?/, '');
  }

  // 设置hash路径（保留现有参数）
  static setHashPath(path: string): void {
    const hashParams = this.getHashParams();
    const cleanPath = path.replace(/^\/|\/$/g, '');
    this.updateHashUrl(hashParams, cleanPath);
  }
}