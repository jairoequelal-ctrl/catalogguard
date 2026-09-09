-- Open exceptions by severity
SELECT severity, COUNT(*) AS exception_count
FROM exceptions
WHERE review_status = 'OPEN'
GROUP BY severity
ORDER BY exception_count DESC;

-- Potential duplicate ISWCs in the internal work view
SELECT iswc_norm, COUNT(*) AS occurrences
FROM internal_work_view
WHERE iswc_norm <> ''
GROUP BY iswc_norm
HAVING COUNT(*) > 1;

-- Records requiring human review
SELECT internal_work_id, external_work_id, match_method, match_confidence
FROM matches
WHERE match_status = 'MANUAL_REVIEW'
ORDER BY match_confidence DESC;

-- Works present only in one source
SELECT *
FROM matches
WHERE match_status IN ('UNMATCHED', 'UNMATCHED_EXTERNAL');
