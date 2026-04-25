import type {
  GuidedChoiceGroup,
  GuidedChoiceOption,
  GuidedConversationPhase,
  GuidedStructureOption,
  GuidedTopicSelectionResponse,
  GuidedTopicSuggestion,
} from '../../../lib/guidedChat';
import type { WorkshopDraftPatchProposal } from '../../../lib/workshopCoauthoring';
import type { ReportPatch, ResearchCandidate, SourceRecord } from './reportDocument';
import type { FormatValidationResult } from '../validators/reportValidation';

export type WorkshopMessageRole = 'user' | 'foli' | 'assistant' | 'bot';

export interface WorkshopChatMessage {
  id: string;
  role: WorkshopMessageRole;
  content: string;
  isStreaming?: boolean;
  draftPatch?: WorkshopDraftPatchProposal;
  reportPatch?: ReportPatch;
  patchValidation?: FormatValidationResult | null;
  researchCandidates?: ResearchCandidate[];
  researchSources?: SourceRecord[];
  phase?: GuidedConversationPhase | null;
  topicSubject?: string;
  topicSuggestions?: GuidedTopicSuggestion[];
  pageRangeOptions?: GuidedTopicSelectionResponse['recommended_page_ranges'];
  structureOptions?: GuidedStructureOption[];
  nextActionOptions?: GuidedChoiceOption[];
  choiceGroups?: GuidedChoiceGroup[];
}
