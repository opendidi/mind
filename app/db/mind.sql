/*
SQLyog Ultimate v10.00 Beta1
MySQL - 5.7.26 : Database - mind
*********************************************************************
*/

/*!40101 SET NAMES utf8 */;

/*!40101 SET SQL_MODE=''*/;

/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
CREATE DATABASE /*!32312 IF NOT EXISTS*/`mind` /*!40100 DEFAULT CHARACTER SET utf8 */;

USE `mind`;

/*Table structure for table `blueprint` */

DROP TABLE IF EXISTS `blueprint`;

CREATE TABLE `blueprint` (
  `id` varchar(33) NOT NULL,
  `name` varchar(255) DEFAULT NULL COMMENT '文件名称',
  `color` varchar(255) DEFAULT NULL COMMENT '默认颜色',
  `penBackground` varchar(255) DEFAULT NULL COMMENT '画笔填充颜色',
  `background` varchar(255) DEFAULT NULL COMMENT '背景颜色',
  `bkImage` varchar(255) DEFAULT NULL COMMENT '背景图片地址',
  `grid` varchar(10) DEFAULT '0' COMMENT '背景网格',
  `gridColor` varchar(255) DEFAULT NULL COMMENT '网格颜色',
  `gridSize` varchar(255) DEFAULT NULL COMMENT '网格大小',
  `gridRotate` varchar(255) DEFAULT NULL COMMENT '网格角度',
  `rule` varchar(10) DEFAULT '0' COMMENT '标尺',
  `ruleColor` varchar(255) DEFAULT NULL COMMENT '标尺颜色',
  `initJs` text COMMENT '初始化JS',
  `pens` text COMMENT '画笔数据',
  `https` text COMMENT 'https数组数据',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `del` int(11) DEFAULT '0' COMMENT '逻辑删除',
  `thumbnail` varchar(255) DEFAULT NULL COMMENT '缩略图',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

/*Table structure for table `categories` */

DROP TABLE IF EXISTS `categories`;

CREATE TABLE `categories` (
  `id` varchar(33) NOT NULL,
  `name` varchar(255) NOT NULL,
  `description` text,
  `sort_order` int(10) unsigned DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `status` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/*Table structure for table `material` */

DROP TABLE IF EXISTS `material`;

CREATE TABLE `material` (
  `id` varchar(33) NOT NULL,
  `name` varchar(255) DEFAULT NULL COMMENT '素材名称',
  `url` varchar(255) DEFAULT NULL COMMENT '绝对路径',
  `file_path` varchar(1024) DEFAULT NULL COMMENT '素材存储路径',
  `thumb_path` varchar(255) DEFAULT NULL COMMENT '缩略图路径',
  `size` bigint(20) DEFAULT NULL COMMENT '素材大小（以字节为单位）',
  `extension` varchar(10) DEFAULT NULL COMMENT '文件扩展名（如 jpg, mp3, mp4 等）',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `description` text COMMENT '素材描述',
  `del` int(11) DEFAULT '0' COMMENT '是否已删除，0正常，1删除',
  `parent_id` varchar(33) DEFAULT NULL COMMENT '如果 parent_id 为 NULL，表示该记录是一个文件夹。\n如果 parent_id 指向其他记录，则该记录为该文件夹中的文件或子文件夹。',
  `type` varchar(255) DEFAULT NULL,
  `lock` int(11) DEFAULT '0' COMMENT '文件锁',
  `sort_order` int(11) DEFAULT '0' COMMENT '排序',
  `path` varchar(255) DEFAULT NULL COMMENT '文件夹路径',
  `user_id` varchar(33) DEFAULT NULL COMMENT '用户ID',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
