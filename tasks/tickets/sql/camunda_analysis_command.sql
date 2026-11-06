-- EXPLAIN ANALYZE for camunda_ticket_ids
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT *
FROM camunda_ticket_ids(
  ticket_type => NULL,
  ticket_number => NULL,
  ticket_title => NULL,
  ticket_status => 'ACTIVE',
  creator_list => NULL,
  processor_list => NULL,
  assignee_list => NULL,
  phase_list => NULL,
  start_time_from => NULL,
  start_time_to => NULL,
  end_time_from => NULL,
  end_time_to => NULL,
  pending_basket_ids => NULL,
  processed_by_basket_ids => NULL,
  user_basket_ids => NULL,
  sort_by => 'create_time',
  sort_order => 'desc',
  limit_count => 50,
  offset_count => 0
);

-- EXPLAIN ANALYZE for camunda_ticket_count
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT camunda_ticket_count(
  ticket_type => NULL,
  ticket_number => NULL,
  ticket_title => NULL,
  ticket_status => 'ACTIVE',
  creator_list => NULL,
  processor_list => NULL,
  assignee_list => NULL,
  phase_list => NULL,
  start_time_from => NULL,
  start_time_to => NULL,
  end_time_from => NULL,
  end_time_to => NULL,
  pending_basket_ids => NULL,
  processed_by_basket_ids => NULL,
  user_basket_ids => NULL
);

-- Combined ids + details for data correctness
WITH ids AS (
  SELECT *
  FROM camunda_ticket_ids(
    ticket_type => NULL,
    ticket_number => NULL,
    ticket_title => NULL,
    ticket_status => 'ACTIVE',
    creator_list => NULL,
    processor_list => NULL,
    assignee_list => NULL,
    phase_list => NULL,
    start_time_from => NULL,
    start_time_to => NULL,
    end_time_from => NULL,
    end_time_to => NULL,
    pending_basket_ids => NULL,
    processed_by_basket_ids => NULL,
    user_basket_ids => NULL,
    sort_by => 'create_time',
    sort_order => 'desc',
    limit_count => 50,
    offset_count => 0
  )
)
SELECT *
FROM camunda_ticket_details(ARRAY(SELECT proc_inst_id_ FROM ids));
