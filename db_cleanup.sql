DELETE FROM qso WHERE hex(title) LIKE '%E280%';
DELETE FROM qso WHERE post_id = 0;
DELETE FROM qso WHERE LENGTH(title) = 0;
DELETE FROM qso WHERE rowid NOT IN (SELECT MIN(rowid) FROM qso GROUP BY post_id);
ALTER TABLE status ADD selected_post integer;
