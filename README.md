# Viral-Marketing

erDiagram
    USERS ||--o{ ACCOUNTS : "1:N"
    ACCOUNTS ||--o{ TRANSACTION_HISTORY : "1:N"

    USERS {
      UUID id PK
      string email UK
      string password
      string nickname
      string name
      string phone
      datetime last_login
      bool is_staff
      bool is_superuser
      bool is_active
      datetime date_joined
    }

    ACCOUNTS {
      UUID id PK
      UUID user_id FK  "-> USERS.id"
      string bank_code "choices: KAKAO/KB/NH/IBK/SC/HANA/WOORI/SHINHAN/ETC"
      string account_number
      string account_type "choices: DEMAND/OVERDRAFT/SAVINGS/ETC"
      decimal balance
      datetime created_at
      datetime updated_at
      UNIQUE (user_id, bank_code, account_number)
      INDEX (user_id, created_at desc)
    }

    TRANSACTION_HISTORY {
      UUID id PK
      UUID account_id FK "-> ACCOUNTS.id"
      decimal amount
      decimal balance_after
      string description
      string io_type   "choices: DEPOSIT/WITHDRAW"
      string method    "choices: CASH/TRANSFER/AUTO/CARD/ETC"
      datetime created_at
      INDEX (account_id, created_at desc)
      INDEX (account_id, io_type)
    }

