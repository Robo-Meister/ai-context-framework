from typing import List, Dict

from caiengine.common.types.ScopeRoleKey import ScopeRoleKey


class Fuser:
    def fuse(self, categorized_data: Dict[ScopeRoleKey, List[dict]]) -> Dict[ScopeRoleKey, dict]:
        fused_results = {}

        for key, data_list in categorized_data.items():
            if not data_list:
                continue

            timestamps = [d['timestamp'] for d in data_list if d.get('timestamp')]
            start_time = min(timestamps)
            end_time = max(timestamps)

            avg_confidence = sum(d.get('confidence', 1.0) for d in data_list) / len(data_list)

            contents = [str(d.get('content', '')) for d in data_list]
            aggregated_content = " | ".join(contents)

            fused_results[key] = {
                'start_time': start_time,
                'end_time': end_time,
                'avg_confidence': avg_confidence,
                'aggregated_content': aggregated_content,
                'count': len(data_list),
            }

        return fused_results
