DELETE FROM qso WHERE hex(title) LIKE '%E280%';
DELETE FROM qso WHERE post_id = 0;
DELETE FROM qso WHERE LENGTH(title) = 0;
DELETE FROM qso WHERE rowid NOT IN (SELECT MIN(rowid) FROM qso GROUP BY post_id);
ALTER TABLE status ADD selected_post integer;
CREATE TABLE progress (
    qso_date integer,
    blog text,
    station text,
    frequency integer,
    offset integer,
    message text);
ALTER TABLE qso RENAME TO post;
ALTER TABLE post ADD COLUMN is_selected integer;
ALTER TABLE status RENAME COLUMN qso_updated TO post_list_updated;
UPDATE settings SET name = 'max_posts' WHERE name = 'max_qsos';
