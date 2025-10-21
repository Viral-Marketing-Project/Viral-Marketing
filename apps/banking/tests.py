# apps/banking/tests.py
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class BaseAPITest(APITestCase):
    def setUp(self):
        # 테스트용 사용자 생성(+활성화)
        self.email = "me@example.com"
        self.password = "pass1234"
        self.user = User.objects.create_user(email=self.email, password=self.password, is_active=True)

        # 로그인 → 쿠키 기반 인증 세팅
        url = reverse("users:login")
        res = self.client.post(url, {"email": self.email, "password": self.password}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)

        # URL들
        self.accounts_list_url = reverse("banking:account-list")
        self.transactions_list_url = reverse("banking:transaction-list")

    # 헬퍼: 계좌 생성
    def _create_account(self, bank_code="KAKAO", account_number="111122223333", account_type="DEMAND"):
        payload = {
            "bank_code": bank_code,
            "account_number": account_number,
            "account_type": account_type,  # models.py: "DEMAND", "OVERDRAFT", "SAVINGS", "ETC"
        }
        res = self.client.post(self.accounts_list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.content)
        return res.json()

    # 헬퍼: 거래 생성
    def _create_transaction(self, account_id, amount="50000.00", io_type="DEPOSIT", method="TRANSFER", description=""):
        payload = {
            "account_id": account_id,
            "amount": amount,
            "io_type": io_type,        # "DEPOSIT" | "WITHDRAW"
            "method": method,          # "CASH"|"TRANSFER"|"AUTO"|"CARD"|"ETC"
            "description": description,
        }
        res = self.client.post(self.transactions_list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.content)
        return res.json()


class AccountsCRUDTests(BaseAPITest):
    """
    Accounts(계좌) 엔드포인트 CRUD 테스트
    - 생성 / 목록 / 상세 / (수정 불가 확인) / 삭제
    """

    def test_account_create_list_retrieve_delete_and_update_not_allowed(self):
        # Create
        acc = self._create_account()
        acc_id = acc["id"]

        # List
        res = self.client.get(self.accounts_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(any(a["id"] == acc_id for a in res.json()))

        # Retrieve
        detail_url = reverse("banking:account-detail", args=[acc_id])
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["id"], acc_id)

        # Update (PUT/PATCH) 금지 확인 → 405
        res = self.client.put(detail_url, {"bank_code": "KB", "account_number": "222233334444", "account_type": "SAVINGS"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        res = self.client.patch(detail_url, {"account_type": "SAVINGS"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Delete
        res = self.client.delete(detail_url)
        self.assertIn(res.status_code, (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK))

        # 확인: 목록에서 사라짐
        res = self.client.get(self.accounts_list_url)
        self.assertFalse(any(a["id"] == acc_id for a in res.json()))


class TransactionsCRUDTests(BaseAPITest):
    """
    Transactions(입출금) 엔드포인트 CRUD 테스트
    - 생성(입금/출금) / 목록 / 필터 / 상세 / 수정 / 삭제
    """

    def test_transaction_crud_with_filters(self):
        # 계좌 1개 생성
        acc = self._create_account()
        acc_id = acc["id"]

        # 거래 생성: 입금 50,000 / 출금 10,000 / 입금 120,000
        t1 = self._create_transaction(acc_id, amount="50000.00", io_type="DEPOSIT", method="TRANSFER", description="급여")
        t2 = self._create_transaction(acc_id, amount="10000.00", io_type="WITHDRAW", method="CARD", description="점심")
        t3 = self._create_transaction(acc_id, amount="120000.00", io_type="DEPOSIT", method="TRANSFER", description="보너스")

        # 목록
        res = self.client.get(self.transactions_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in res.json()]
        self.assertTrue(all(t in ids for t in [t1["id"], t2["id"], t3["id"]]))

        # 필터 1: io_type=DEPOSIT
        res = self.client.get(self.transactions_list_url, {"io_type": "DEPOSIT"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertTrue(all(item["io_type"] == "DEPOSIT" for item in data))
        self.assertTrue(any(item["id"] == t1["id"] for item in data))
        self.assertTrue(any(item["id"] == t3["id"] for item in data))
        self.assertFalse(any(item["id"] == t2["id"] for item in data))

        # 필터 2: method=TRANSFER & min_amount=60000
        res = self.client.get(self.transactions_list_url, {"method": "TRANSFER", "min_amount": "60000"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        # 120,000 입금만 남아야 함
        self.assertTrue(any(item["id"] == t3["id"] for item in data))
        self.assertFalse(any(item["id"] == t1["id"] for item in data))  # 50,000 < 60,000
        self.assertFalse(any(item["id"] == t2["id"] for item in data))  # method=CARD

        # 상세
        detail_url = reverse("banking:transaction-detail", args=[t2["id"]])
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["id"], t2["id"])

        # 수정(허용 필드: description, method)
        res = self.client.patch(detail_url, {"description": "메모 정정", "method": "TRANSFER"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["description"], "메모 정정")
        self.assertEqual(res.json()["method"], "TRANSFER")

        # 삭제
        res = self.client.delete(detail_url)
        self.assertIn(res.status_code, (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK))

        # 확인: 목록에서 사라짐
        res = self.client.get(self.transactions_list_url)
        self.assertFalse(any(item["id"] == t2["id"] for item in res.json()))
from django.test import TestCase

# Create your tests here.
