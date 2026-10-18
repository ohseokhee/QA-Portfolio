-- Day 59 : fc_qa_lab 스키마 (모의 게임 서버 상점·재화 API용)
-- 재화: FC(유료 재화), BP(무료 재화)
-- 실행: py day59_apply_schema.py (재실행 시 테이블을 지우고 시드 데이터로 초기화)

CREATE DATABASE IF NOT EXISTS fc_qa_lab CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fc_qa_lab;

DROP TABLE IF EXISTS currency_transactions;
DROP TABLE IF EXISTS purchase_history;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS account_currency;
DROP TABLE IF EXISTS auth_tokens;
DROP TABLE IF EXISTS shop_items;
DROP TABLE IF EXISTS accounts;

-- 계정
CREATE TABLE accounts (
    account_id    INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(20)  NOT NULL UNIQUE,
    password_hash CHAR(64)     NOT NULL,            -- SHA-256 hex
    nickname      VARCHAR(30)  NOT NULL,
    role          ENUM('USER', 'ADMIN')     NOT NULL DEFAULT 'USER',
    status        ENUM('ACTIVE', 'BANNED')  NOT NULL DEFAULT 'ACTIVE',
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 로그인 토큰 (만료 토큰 테스트를 위해 DB에 저장)
CREATE TABLE auth_tokens (
    token       CHAR(64)  PRIMARY KEY,
    account_id  INT       NOT NULL,
    issued_at   DATETIME  NOT NULL,
    expires_at  DATETIME  NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- 재화 잔액 (계정 x 재화 종류)
CREATE TABLE account_currency (
    account_id     INT     NOT NULL,
    currency_type  ENUM('FC', 'BP') NOT NULL,
    balance        BIGINT  NOT NULL DEFAULT 0,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, currency_type),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    CONSTRAINT chk_balance_range CHECK (balance BETWEEN 0 AND 99999999)
);

-- 상점 아이템
CREATE TABLE shop_items (
    item_id           INT PRIMARY KEY,
    name              VARCHAR(50) NOT NULL,
    item_type         ENUM('PLAYER_PACK', 'BOOST', 'COSMETIC') NOT NULL,
    currency_type     ENUM('FC', 'BP') NOT NULL,
    price             INT     NOT NULL,
    max_per_purchase  INT     NOT NULL,     -- 1회 구매 최대 수량
    max_owned         INT     NOT NULL,     -- 인벤토리 보유 상한
    is_on_sale        TINYINT(1) NOT NULL DEFAULT 1
);

-- 인벤토리
CREATE TABLE inventory (
    account_id  INT NOT NULL,
    item_id     INT NOT NULL,
    quantity    INT NOT NULL DEFAULT 0,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, item_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (item_id) REFERENCES shop_items(item_id)
);

-- 구매 이력 (request_id = 클라이언트가 보내는 멱등성 키)
CREATE TABLE purchase_history (
    purchase_id    BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id     INT         NOT NULL,
    item_id        INT         NOT NULL,
    quantity       INT         NOT NULL,
    unit_price     INT         NOT NULL,
    total_price    BIGINT      NOT NULL,
    currency_type  ENUM('FC', 'BP') NOT NULL,
    request_id     VARCHAR(64) NOT NULL,
    created_at     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_account_request (account_id, request_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (item_id) REFERENCES shop_items(item_id)
);

-- 재화 변동 이력 (지급 +, 구매 -)
CREATE TABLE currency_transactions (
    tx_id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id     INT     NOT NULL,
    currency_type  ENUM('FC', 'BP') NOT NULL,
    amount         BIGINT  NOT NULL,                 -- 부호 있음: 지급 +, 차감 -
    balance_after  BIGINT  NOT NULL,
    reason         ENUM('GRANT', 'PURCHASE') NOT NULL,
    purchase_id    BIGINT  NULL,
    operator_id    INT     NULL,                     -- 지급한 운영자 계정
    memo           VARCHAR(100) NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (purchase_id) REFERENCES purchase_history(purchase_id)
);

-- 시드 데이터 (로컬 모의 서버 전용 테스트 계정, 비밀번호는 명세 참고)
INSERT INTO accounts (account_id, username, password_hash, nickname, role, status) VALUES
    (1, 'qa_user1',  SHA2('Test1234!', 256), '테스터1',   'USER',  'ACTIVE'),
    (2, 'qa_user2',  SHA2('Test1234!', 256), '테스터2',   'USER',  'ACTIVE'),
    (3, 'qa_admin',  SHA2('Admin1234!', 256), '운영자',   'ADMIN', 'ACTIVE'),
    (4, 'qa_banned', SHA2('Test1234!', 256), '제재계정', 'USER',  'BANNED');

INSERT INTO account_currency (account_id, currency_type, balance) VALUES
    (1, 'FC', 5000),  (1, 'BP', 200000),
    (2, 'FC', 0),     (2, 'BP', 0),
    (3, 'FC', 0),     (3, 'BP', 0),
    (4, 'FC', 1000),  (4, 'BP', 1000);

INSERT INTO shop_items (item_id, name, item_type, currency_type, price, max_per_purchase, max_owned, is_on_sale) VALUES
    (101, '프리미엄 선수팩', 'PLAYER_PACK', 'FC', 1000,  10, 999, 1),
    (102, '일반 선수팩',     'PLAYER_PACK', 'BP', 50000, 10, 999, 1),
    (103, '훈련 부스터',     'BOOST',       'BP', 10000, 10, 999, 1),
    (104, '클럽 유니폼 세트', 'COSMETIC',    'FC', 3000,  1,   1,  1),
    (105, '이벤트 한정팩',   'PLAYER_PACK', 'FC', 500,   10, 999, 0);
