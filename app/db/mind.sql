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

/*Data for the table `categories` */

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

/*Data for the table `material` */

insert  into `material`(`id`,`name`,`url`,`file_path`,`thumb_path`,`size`,`extension`,`created_at`,`updated_at`,`description`,`del`,`parent_id`,`type`,`lock`,`sort_order`,`path`,`user_id`) values ('10894dadb1dc44188929b14e8d7dbfaf','6a2ae9972c2e30f71b22cb745328445e','http://192.168.1.78:9000/pano/1755229231/6a2ae9972c2e30f71b22cb745328445e.png',NULL,'',124494,'png','2025-08-15 11:40:31','2025-08-15 11:40:31',NULL,0,'be708e3035354e70acc3789931eecdbe','.png',0,0,NULL,NULL),('3c54e7dcb3c04b3b87a118a09b2dd0af','zFpmhzyrxz9p7',NULL,NULL,NULL,NULL,NULL,'2025-08-15 12:01:08','2025-08-15 12:01:08',NULL,0,'be708e3035354e70acc3789931eecdbe','dir',0,0,'RnNKDYZ5mf5RX/zFpmhzyrxz9p7',NULL),('98cffdb32f90430c9f0718009bea91b9','084eCAebZaPPhEJVKbKIK1YEkhBBAq','http://192.168.1.78:9000/pano/1755251446/084eCAebZaPPhEJVKbKIK1YEkhBBAq.png',NULL,'',1824252,'png','2025-08-15 17:50:46','2025-08-15 17:50:46',NULL,0,'be708e3035354e70acc3789931eecdbe','.png',0,0,NULL,NULL),('be708e3035354e70acc3789931eecdbe','RnNKDYZ5mf5RX',NULL,NULL,NULL,NULL,NULL,'2025-08-15 10:56:26','2025-08-15 10:56:26',NULL,0,NULL,'dir',0,0,'RnNKDYZ5mf5RX',NULL),('d31b4b8a8ef640e8aaf58360f952de53','f12c41c38266e1a1f3f63861e80eeed5','http://192.168.1.78:9000/pano/1755251651/f12c41c38266e1a1f3f63861e80eeed5.gif',NULL,'',544865,'gif','2025-08-15 17:54:11','2025-08-15 17:54:11',NULL,0,'be708e3035354e70acc3789931eecdbe','.gif',0,0,NULL,NULL);

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
