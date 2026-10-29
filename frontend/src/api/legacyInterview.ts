// Archived V3 interview types. These pages and APIs are offline in V4.
export interface LegacyComponents {
    schemas: {
        DifyInterviewField: {
            /** Value */
            value: string;
            /** Evidence Message Ids */
            evidence_message_ids: string[];
            /**
             * Source
             * @enum {string}
             */
            source: "USER_INPUT" | "USER_EDIT";
        };
        /** DifyInterviewQuestion */
        DifyInterviewQuestion: {
            /** Text */
            text: string;
            /**
             * Target Field
             * @enum {string}
             */
            target_field: "target_user" | "usage_scenario" | "user_goal" | "current_problem" | "expected_result" | "proposed_solution" | "frequency" | "impact_scope" | "bug_steps" | "actual_result" | "environment";
            /**
             * Reason Code
             * @enum {string}
             */
            reason_code: "MISSING_CORE_FIELD" | "MISSING_BUG_FIELD" | "CLARIFY_CONFLICT" | "SEPARATE_PROBLEM_FROM_SOLUTION" | "CLARIFY_MULTIPLE_REQUESTS" | "MISSING_RECOMMENDED_FIELD";
        };
        /** HTTPValidationError */
        InterviewActionType: "INITIAL" | "ANSWER" | "SKIP" | "UNKNOWN" | "DIRECT_SUMMARY";
        /** InterviewAttachmentRead */
        InterviewAttachmentRead: {
            /** Id */
            id: string;
            /** Session Id */
            session_id: string | null;
            /** Message Id */
            message_id: string | null;
            /** Uploaded By */
            uploaded_by: string | null;
            /** Original Name */
            original_name: string;
            /** Mime Type */
            mime_type: string;
            /** Size Bytes */
            size_bytes: number;
            /** Sha256 */
            sha256: string;
            /** Preview Url */
            preview_url: string;
            /**
             * Created Time
             * Format: date-time
             */
            created_time: string;
        };
        /** InterviewConfirmRequest */
        InterviewMessageRead: {
            /** Id */
            id: string;
            /** Session Id */
            session_id: string;
            /** Sequence No */
            sequence_no: number;
            role: LegacyComponents["schemas"]["InterviewMessageRole"];
            /** Content */
            content: string;
            action_type: LegacyComponents["schemas"]["InterviewActionType"] | null;
            /** Target Field */
            target_field: string | null;
            /** Reason Code */
            reason_code: string | null;
            /** Client Message Id */
            client_message_id: string | null;
            /** Agent Run Id */
            agent_run_id: string | null;
            /** Attachments */
            attachments: LegacyComponents["schemas"]["InterviewAttachmentRead"][];
            /**
             * Created Time
             * Format: date-time
             */
            created_time: string;
        };
        /**
         * InterviewMessageRole
         * @enum {string}
         */
        InterviewMessageRole: "USER" | "AGENT" | "SYSTEM_EVENT";
        /** InterviewSessionRead */
        InterviewSessionRead: {
            /** Id */
            id: string;
            /** Project Id */
            project_id: string;
            /** Created By */
            created_by: string | null;
            source_channel: LegacyComponents["schemas"]["SourceChannel"];
            project_resolve_mode: LegacyComponents["schemas"]["ProjectResolveMode"];
            status: LegacyComponents["schemas"]["InterviewStatus"];
            /** Raw Content */
            raw_content: string;
            request_type: LegacyComponents["schemas"]["RequirementType"] | null;
            /** Current Card */
            current_card: {
                [key: string]: LegacyComponents["schemas"]["DifyInterviewField"] | null;
            };
            /** Skipped Fields */
            skipped_fields: ("target_user" | "usage_scenario" | "user_goal" | "current_problem" | "expected_result" | "proposed_solution" | "frequency" | "impact_scope" | "bug_steps" | "actual_result" | "environment")[];
            /** Completeness Score */
            completeness_score: number;
            /** Round Count */
            round_count: number;
            /** Consecutive Skip Count */
            consecutive_skip_count: number;
            /** Stop Reason */
            stop_reason: string | null;
            /** Summary Title */
            summary_title: string | null;
            /** Clarified Content */
            clarified_content: string | null;
            /** Requirement Id */
            requirement_id: string | null;
            current_question: LegacyComponents["schemas"]["DifyInterviewQuestion"] | null;
            /** Messages */
            messages: LegacyComponents["schemas"]["InterviewMessageRead"][];
            /** Agent Error Code */
            agent_error_code: string | null;
            /**
             * Created Time
             * Format: date-time
             */
            created_time: string;
            /**
             * Updated Time
             * Format: date-time
             */
            updated_time: string;
        };
        /**
         * InterviewStatus
         * @enum {string}
         */
        InterviewStatus: "DRAFT" | "INTERVIEWING" | "CONFIRMING" | "SUBMITTED" | "ABANDONED" | "FAILED";
        /** InterviewSummaryUpdate */
        ProjectResolveMode: "USER_SELECTED" | "ENTRY_BOUND" | "CHANNEL_MAPPED";
        /**
         * ProjectStatus
         * @enum {string}
         */
        RequirementType: "NEW_FEATURE" | "BUG" | "OPTIMIZATION";
        /** SessionCreateRequest */
        SourceChannel: "MANAGEMENT_WEB" | "PRODUCT_WEB" | "MINI_PROGRAM" | "WECHAT" | "WECOM" | "FEISHU" | "OTHER";
        /** TaskCreate */
    }
}
