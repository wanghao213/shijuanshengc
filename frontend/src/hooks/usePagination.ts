/** 分页 Hook */

import { useCallback, useState } from 'react';

interface PaginationState {
  page: number;
  pageSize: number;
  total: number;
}

interface UsePaginationReturn extends PaginationState {
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  setTotal: (total: number) => void;
  onChange: (page: number, pageSize: number) => void;
}

export function usePagination(defaultPageSize: number = 20): UsePaginationReturn {
  const [state, setState] = useState<PaginationState>({
    page: 1,
    pageSize: defaultPageSize,
    total: 0,
  });

  const setPage = useCallback((page: number) => setState((s) => ({ ...s, page })), []);
  const setPageSize = useCallback((pageSize: number) => setState((s) => ({ ...s, pageSize, page: 1 })), []);
  const setTotal = useCallback((total: number) => setState((s) => ({ ...s, total })), []);
  const onChange = useCallback((page: number, pageSize: number) => setState((s) => ({ ...s, page, pageSize })), []);

  return { ...state, setPage, setPageSize, setTotal, onChange };
}
