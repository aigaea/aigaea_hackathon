CREATE DATABASE hack_hackathon charset utf8mb4;
-- ------------------------------------------------------------------------

-- Table: User training record
DROP TABLE IF EXISTS `hack_emotion_training`;
CREATE TABLE `hack_emotion_training`
(
    `id`                  int           NOT NULL AUTO_INCREMENT COMMENT 'id',
    
    `address`             varchar(64)   DEFAULT '',
    `detail`              varchar(64)   DEFAULT '', -- emotion_detail
    `status`              int           DEFAULT 0 , -- 0 - nothing / 1 - aitraining / 2 - deeptraining
    `date`                varchar(32)   DEFAULT '',

    `trainid_eth`         int           DEFAULT 0 , -- hack_emotion_train
    `trainid_base`        int           DEFAULT 0 , -- hack_emotion_train
    `trainid_avax`        int           DEFAULT 0 , -- hack_emotion_train
    `trainid_bsc`         int           DEFAULT 0 , -- hack_emotion_train

    `created_time`        datetime      DEFAULT NOW(),
    `updated_time`        datetime      DEFAULT NULL ,
    PRIMARY KEY (`id`)  USING BTREE,
    INDEX idx_address (address)
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_general_ci ROW_FORMAT = Dynamic;


-- Table: User on-chain emotion record
DROP TABLE IF EXISTS `hack_emotion_onchain`;
CREATE TABLE `hack_emotion_onchain`
(
    `id`                  int           NOT NULL AUTO_INCREMENT COMMENT 'id',

    `address`             varchar(64)   DEFAULT '',
    `tx_chainid`          varchar(32)   DEFAULT '',  -- chainid
    `tx_blockid`          varchar(32)   DEFAULT '',  -- blockid
    `tx_hash`             varchar(128)  DEFAULT '',
    `tx_date`             varchar(32)   DEFAULT '',
    `cool_address`        varchar(64)   DEFAULT '',
    `cool_amount`         int           DEFAULT 0 ,
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
ALTER TABLE hack_emotion_onchain ADD UNIQUE (tx_hash);

-- ------------------------------------------------------------------------

-- Table: Emotional cycle
DROP TABLE IF EXISTS `hack_emotions`;
CREATE TABLE `hack_emotions`
(
    `id`                   int          NOT NULL AUTO_INCREMENT COMMENT 'id',

    `chain_id`             int       DEFAULT 0   COMMENT 'id',
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

-- ------------------------------------------------------------------------

INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (11155111, 1, 1800, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (11155111, 2, 7200, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (11155111, 3, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (11155111, 4, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (11155111, 5, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (11155111, 6, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (11155111, 7, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (11155111, 8, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (11155111, 9, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (11155111,10, 86400, 280000, 1000000, 80, 0);

INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (84532, 1, 1800, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (84532, 2, 7200, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (84532, 3, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (84532, 4, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (84532, 5, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (84532, 6, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (84532, 7, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (84532, 8, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (84532, 9, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (84532,10, 86400, 280000, 1000000, 80, 0);

INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (43113, 1, 1800, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (43113, 2, 7200, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (43113, 3, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (43113, 4, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (43113, 5, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (43113, 6, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (43113, 7, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (43113, 8, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (43113, 9, 86400, 280000, 1000000, 80, 0);
INSERT INTO hack_emotions (chain_id, period_id, period_duration, period_price, period_putmoney, period_proportion, status) VALUES (43113,10, 86400, 280000, 1000000, 80, 0);

-- ------------------------------------------------------------------------
