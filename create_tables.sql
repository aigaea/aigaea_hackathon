CREATE DATABASE gaea_hackathon charset utf8mb4;
-- ------------------------------------------------------------------------

-- Table: Emotional cycle
DROP TABLE IF EXISTS `gaea_emotions`;
CREATE TABLE `gaea_emotions`
(
    `id`                   int          NOT NULL AUTO_INCREMENT COMMENT 'id',

    `period_id`            int       DEFAULT 0   COMMENT 'id',
    `period_duration`      int       DEFAULT 0   COMMENT 'duration',
    `period_price`         int       DEFAULT 0   COMMENT 'price',
    `period_putmoney`      int       DEFAULT 0   COMMENT 'putmoney',
    `period_proportion`    int       DEFAULT 80  COMMENT 'userproportion',
    `period_start`         int       DEFAULT 0   COMMENT 'startstamp',
    `period_end`           int       DEFAULT 0   COMMENT 'endstamp',
    `period_emotion`       int       DEFAULT 0   COMMENT 'emotion',
    `period_average`       int       DEFAULT 0   COMMENT 'average',
    `period_reward`        int       DEFAULT 0   COMMENT 'reward',
    `period_total`         int       DEFAULT 0   COMMENT 'total',
    `emotion_positive`     int       DEFAULT 0   COMMENT 'positive',
    `emotion_neutral`      int       DEFAULT 0   COMMENT 'neutral',
    `emotion_negative`     int       DEFAULT 0   COMMENT 'negative',
    `status`               int       DEFAULT 0   COMMENT 'status',    -- 0-not started, 1-in progress, 2-completed

    `created_time`        datetime      DEFAULT NOW(),
    `updated_time`        datetime      DEFAULT NULL ,
    PRIMARY KEY (`id`)  USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;

INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES ( 1, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES ( 2, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES ( 3, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES ( 4, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES ( 5, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES ( 6, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES ( 7, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES ( 8, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES ( 9, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (10, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (11, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (12, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (13, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (14, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (15, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (16, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (17, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (18, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (19, 86400, 280000, 1000000, 80, 0);
INSERT INTO gaea_emotions (period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (20, 86400, 280000, 1000000, 80, 0);

-- ------------------------------------------------------------------------

-- Table: User training record
DROP TABLE IF EXISTS `gaea_emotion_training`;
CREATE TABLE `gaea_emotion_training`
(
    `id`                  int           NOT NULL AUTO_INCREMENT COMMENT 'id',
    
    `address`             varchar(64)   DEFAULT '',
    `detail`              varchar(64)   DEFAULT '', -- emotion_detail
    `status`              int           DEFAULT 0 , -- 0 - nothing / 1 - aitraining / 2 - deeptraining
    `date`                varchar(32)   DEFAULT '',

    `trainid`             int           DEFAULT 0 , -- gaea_emotion_train

    `created_time`        datetime      DEFAULT NOW(),
    `updated_time`        datetime      DEFAULT NULL ,
    PRIMARY KEY (`id`)  USING BTREE,
    INDEX idx_address (address)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;


-- Table: User on-chain emotion record
DROP TABLE IF EXISTS `gaea_emotion_onchain`;
CREATE TABLE `gaea_emotion_onchain`
(
    `id`                  int           NOT NULL AUTO_INCREMENT COMMENT 'id',

    `address`             varchar(64)   DEFAULT '',
    `tx_chainid`          varchar(32)   DEFAULT '',  -- chainid
    `tx_blockid`          varchar(32)   DEFAULT '',  -- blockid
    `tx_hash`             varchar(128)  DEFAULT '',
    `tx_date`             varchar(32)   DEFAULT '',
    `cool_address`        varchar(64)   DEFAULT '',
    `cool_amount`         int           DEFAULT 0 ,
    `contract`            int           DEFAULT 1 ,
    `period_id`           int           DEFAULT 0  COMMENT 'ID',
    `period_emotion`      int           DEFAULT 0  COMMENT 'emotion',
    `period_uuid`         int           DEFAULT 0  COMMENT 'uuid',

    `status`              TINYINT       DEFAULT 0 , -- 0 pending, 1 success, 2 failed
    `note`                varchar(256)  DEFAULT '',

    `created_time`        datetime      DEFAULT NOW(),
    `updated_time`        datetime      DEFAULT NULL ,
    PRIMARY KEY (`id`)  USING BTREE,
    INDEX idx_address (address),
    INDEX idx_tx_hash (tx_hash)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;
ALTER TABLE gaea_emotion_onchain ADD UNIQUE (tx_hash);

-- ------------------------------------------------------------------------