import { notify, alert, extractApiError } from '../utils/notify';

export function useNotify() {
  return { notify, alert, extractApiError };
}

export default useNotify;