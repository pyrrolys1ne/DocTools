DocTools 桌面版（Windows x64）
============================

使用：
1. 解压后运行 DocTools.exe。
2. 程序会自动启动随包的本地服务（docserver\），退出时自动关闭。
3. 所有文件均在本机处理，不会上传。

说明：
- 去页眉 / 去页脚、图片压缩、PDF 合并 / 拆分 / 转图片等无需额外安装。
- Word 转 PDF / PPT 转 PDF 依赖本机安装的 Microsoft Office（Windows 桌面版）。
- PDF 转 Word 为有损转换，复杂排版与扫描件效果有限。

目录结构：
DocTools.exe        桌面客户端
docserver\          本地 API 服务（由 web/ 后端打包而成）
README.txt          本文件