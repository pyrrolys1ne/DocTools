/**
 * 操作注册表：首页宫格、占位文案、扩展名等所有操作相关配置集中在此，
 * 页面组件只负责读取，避免各页面重复维护映射表。
 */

import {
  Eraser,
  FileImage,
  FileText,
  Files,
  Image as ImageIcon,
  Presentation,
  Shrink,
  Split,
  type LucideIcon,
} from "lucide-react";

import type { BatchOp, Operation } from "../types";

export type { BatchOp, Operation };

/** 视图切换：首页 / 各操作页面。 */
export type View = "home" | Operation;

/** 目录批量 / 单个文件。 */
export type Scope = "dir" | "file";

/** 去页眉版块的可选目标：去页眉 / 去页脚 / 两者同时。 */
export type RemoveTarget = "remove-headers" | "remove-footers" | "remove-headers-footers";

export const REMOVE_TARGETS: RemoveTarget[] = [
  "remove-headers",
  "remove-footers",
  "remove-headers-footers",
];

export const TARGET_LABEL: Record<RemoveTarget, string> = {
  "remove-headers": "去页眉",
  "remove-footers": "去页脚",
  "remove-headers-footers": "去页眉页脚",
};

/** 各批量操作允许的源文件扩展名（文件选择器过滤用）。 */
export const BATCH_EXTS: Record<BatchOp, string> = {
  "remove-headers": ".docx",
  "remove-footers": ".docx",
  "remove-headers-footers": ".docx",
  "word-to-pdf": ".docx,.doc",
  "ppt-to-pdf": ".pptx,.ppt",
  "image-to-pdf": ".png,.jpg,.jpeg,.bmp,.gif,.webp,.tif,.tiff",
  "pdf-to-word": ".pdf",
  "pdf-to-ppt": ".pdf",
  "compress-images": ".png,.jpg,.jpeg,.bmp,.gif,.webp,.tif,.tiff",
};

const HEADER_FOOTER_PLACEHOLDER = {
  dir: "选择包含 .docx 的目录",
  file: "选择或拖入 .docx 文件",
};

const PDF_PLACEHOLDER = {
  dir: "选择包含 .pdf 的目录",
  file: "选择或拖入 .pdf 文件",
};

const IMAGE_PLACEHOLDER = {
  dir: "选择包含图片（png/jpg/…）的目录",
  file: "选择或拖入图片（png/jpg/…）",
};

/** 各批量操作的源路径占位说明（行内显示在输入框内）。 */
export const SOURCE_PLACEHOLDER: Record<BatchOp, { dir: string; file: string }> = {
  "remove-headers": HEADER_FOOTER_PLACEHOLDER,
  "remove-footers": HEADER_FOOTER_PLACEHOLDER,
  "remove-headers-footers": HEADER_FOOTER_PLACEHOLDER,
  "word-to-pdf": { dir: "选择包含 .docx/.doc 的目录", file: "选择或拖入 .docx/.doc 文件" },
  "ppt-to-pdf": { dir: "选择包含 .pptx/.ppt 的目录", file: "选择或拖入 .pptx/.ppt 文件" },
  "image-to-pdf": IMAGE_PLACEHOLDER,
  "pdf-to-word": PDF_PLACEHOLDER,
  "pdf-to-ppt": PDF_PLACEHOLDER,
  "compress-images": IMAGE_PLACEHOLDER,
};

const HEADER_FOOTER_OUTPUT = {
  dir: "默认生成到源目录旁的 *_cleaned 文件夹",
  file: "默认生成到源文件旁的 *_cleaned.docx",
};

/** 各批量操作的输出目录占位说明（标注默认生成的位置）。 */
export const OUTPUT_PLACEHOLDER: Record<BatchOp, { dir: string; file: string }> = {
  "remove-headers": HEADER_FOOTER_OUTPUT,
  "remove-footers": HEADER_FOOTER_OUTPUT,
  "remove-headers-footers": HEADER_FOOTER_OUTPUT,
  "word-to-pdf": {
    dir: "默认生成到源目录旁的 *_pdf 文件夹",
    file: "默认生成到源文件旁的同名 .pdf",
  },
  "ppt-to-pdf": {
    dir: "默认生成到源目录旁的 *_pdf 文件夹",
    file: "默认生成到源文件旁的同名 .pdf",
  },
  "image-to-pdf": {
    dir: "默认生成到源目录旁 *_images 文件夹的 merged.pdf",
    file: "默认生成到源文件旁 *_images 文件夹的 merged.pdf",
  },
  "pdf-to-word": {
    dir: "默认生成到源目录旁的 *_docx 文件夹",
    file: "默认生成到源文件旁的同名 .docx",
  },
  "pdf-to-ppt": {
    dir: "默认生成到源目录旁的 *_pptx 文件夹",
    file: "默认生成到源文件旁的同名 .pptx",
  },
  "compress-images": {
    dir: "默认生成到源目录旁的 *_compressed 文件夹",
    file: "默认生成到源文件旁的同名文件",
  },
};

/** 首页功能宫格条目。 */
export interface OperationMeta {
  op: Operation;
  title: string;
  desc: string;
  icon: LucideIcon;
  accent: string;
}

/** 首页功能宫格：六项转换置顶成对排列，其余功能紧随，大小一致。 */
export const OPERATIONS_META: OperationMeta[] = [
  { op: "word-to-pdf", title: "Word 转 PDF", desc: ".docx/.doc 转为 PDF", icon: FileText, accent: "from-sky-500 to-blue-600" },
  { op: "pdf-to-word", title: "PDF 转 Word", desc: "PDF 转为可编辑的 Word", icon: FileText, accent: "from-cyan-500 to-teal-500" },
  { op: "ppt-to-pdf", title: "PPT 转 PDF", desc: ".pptx/.ppt 转为 PDF", icon: Presentation, accent: "from-orange-500 to-amber-500" },
  { op: "pdf-to-ppt", title: "PDF 转 PPT", desc: "PDF 每页做成一张幻灯片", icon: Presentation, accent: "from-fuchsia-500 to-purple-500" },
  { op: "image-to-pdf", title: "图片转 PDF", desc: "多张图片合成一个 PDF", icon: ImageIcon, accent: "from-emerald-500 to-teal-500" },
  { op: "pdf-to-images", title: "PDF 转图片", desc: "PDF 每页导出一张 PNG", icon: FileImage, accent: "from-teal-500 to-cyan-600" },
  { op: "merge-pdf", title: "合并 PDF", desc: "把多个 PDF 合成一个", icon: Files, accent: "from-violet-500 to-purple-500" },
  { op: "split-pdf", title: "拆分 PDF", desc: "每页一个或按页码范围", icon: Split, accent: "from-rose-500 to-pink-500" },
  { op: "remove-headers", title: "去页眉 / 去页脚", desc: "移除 Word 页眉、页脚", icon: Eraser, accent: "from-blue-500 to-indigo-500" },
  { op: "compress-images", title: "图片压缩", desc: "压缩图片体积，可选质量", icon: Shrink, accent: "from-amber-500 to-orange-600" },
];

/** 图片压缩质量档位。 */
export const QUALITY_LEVELS = [
  { label: "高", value: 90 },
  { label: "中", value: 80 },
  { label: "低", value: 60 },
];
