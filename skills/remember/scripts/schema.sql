-- NocoDB-friendly schema for the remember skill.
-- Adjust field types if your deployment uses different attachment or text defaults.

CREATE TABLE IF NOT EXISTS `ItemsV2` (
  `Id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `Name` VARCHAR(255) NOT NULL,
  `Content` TEXT NULL,
  `Location` TEXT NULL,
  `Type` VARCHAR(64) NULL,
  `Note` TEXT NULL,
  `Photo` JSON NULL,
  `CreatedAt` DATETIME NULL,
  `UpdatedAt` DATETIME NULL,
  PRIMARY KEY (`Id`),
  KEY `idx_items_name` (`Name`),
  KEY `idx_items_type` (`Type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
