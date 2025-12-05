from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Any

from src.sheets.google_client import GoogleSheetsClient

T = TypeVar("T")


class BaseSheetRepository(ABC, Generic[T]):
    """
    Google Sheets 기반 시트 하나를 대상으로 하는 공통 Repository 베이스 클래스.

    - sheet_name: 시트 이름 (예: "Position", "T_Ledger")
    - header_row: 헤더가 위치한 행 번호 (예: 1)
    - data_start_row: 실제 데이터가 시작되는 행 번호 (예: 2)
    - columns: 컬럼 이름 리스트 (헤더 기준) — 생성기는 스키마에서 자동 추출
    """

    def __init__(
        self,
        client: GoogleSheetsClient,
        sheet_name: str,
        header_row: int,
        data_start_row: int,
        columns: List[str],
    ) -> None:
        self.client = client
        self.sheet_name = sheet_name
        self.header_row = header_row
        self.data_start_row = data_start_row
        self.columns = columns

    @property
    def last_column_letter(self) -> str:
        """
        스키마에서 컬럼 순서를 보장해주므로, 가장 오른쪽 컬럼만 알면 Range를 구성할 수 있다.
        기본 구현에서는 len(columns)에 맞춰 A,B,C...를 단순 변환해도 되지만,
        실제 구현에서는 스키마에서 column letter를 함께 넘겨 받는 방식으로 확장 가능하다.
        이 Base 클래스에서는 컬럼 개수만큼 A,B,C,... 알파벳을 생성하는 간단 버전으로 둔다.
        """
        index = len(self.columns) - 1
        return self._index_to_column_letter(index)

    @staticmethod
    def _index_to_column_letter(idx: int) -> str:
        """
        0 → A, 1 → B, ..., 25 → Z, 26 → AA ...
        """
        result = []
        n = idx
        while True:
            n, r = divmod(n, 26)
            result.append(chr(ord("A") + r))
            if n == 0:
                break
            n -= 1
        return "".join(reversed(result))

    def _normalize_row(self, row: List[Any]) -> List[Any]:
        """
        Google Sheets API는 뒤쪽 빈 셀을 생략할 수 있으므로,
        columns 길이에 맞춰 오른쪽을 패딩해준다.
        """
        if len(row) < len(self.columns):
            row = row + [""] * (len(self.columns) - len(row))
        return row[: len(self.columns)]

    def fetch_all(self) -> List[T]:
        """
        시트 전체 데이터를 읽어 T 타입 리스트로 반환.
        """
        if not self.columns:
            return []

        first_col_letter = "A"
        last_col_letter = self.last_column_letter
        range_a1 = f"{first_col_letter}{self.data_start_row}:{last_col_letter}"

        values = self.client.read_range(self.sheet_name, range_a1)

        results: List[T] = []
        for row in values:
            # 완전히 비어있는 행은 스킵
            if not row or all((str(v).strip() == "" for v in row)):
                continue
            normalized = self._normalize_row(row)
            entity = self.parse_row(normalized)
            results.append(entity)
        return results

    @abstractmethod
    def parse_row(self, row: List[Any]) -> T:
        """
        한 행(row)을 도메인 엔티티로 변환하는 로직.
        각 시트별 Repository에서 구현한다.
        """
        raise NotImplementedError
