import apiClient from "./client";
import { endpoints } from "./endpoints";

// ==================== Types ====================

export interface ProblemCategory {
  id: string;
  slug: string;
  name: string;
  description?: string | null;
}

export interface ProblemCause {
  id: string;
  category_id: string;
  slug: string;
  name: string;
  description?: string | null;
  detection_hints: string[];
  default_priority: number;
}

export interface ProblemSolution {
  id: string;
  cause_id: string;
  slug: string;
  title: string;
  summary?: string | null;
  instructions: string;
  step_order: number;
  requires_escalation: boolean;
}

export interface ProblemCategoryCreate {
  slug: string;
  name: string;
  description?: string | null;
}

export interface ProblemCategoryUpdate {
  slug?: string;
  name?: string;
  description?: string | null;
}

export interface ProblemCauseCreate {
  category_id: string;
  slug: string;
  name: string;
  description?: string | null;
  detection_hints?: string[];
  default_priority?: number;
}

export interface ProblemCauseUpdate {
  slug?: string;
  name?: string;
  description?: string | null;
  detection_hints?: string[];
  default_priority?: number;
}

export interface ProblemSolutionCreate {
  cause_id: string;
  slug: string;
  title: string;
  summary?: string | null;
  instructions: string;
  step_order?: number;
  requires_escalation?: boolean;
}

export interface ProblemSolutionUpdate {
  slug?: string;
  title?: string;
  summary?: string | null;
  instructions?: string;
  step_order?: number;
  requires_escalation?: boolean;
}

export interface TroubleshootingCatalogImport {
  version?: string;
  problems: Array<{
    slug: string;
    name: string;
    severity: "info" | "low" | "medium" | "high" | "critical";
    description?: string;
    causes: Array<{
      slug: string;
      name: string;
      description?: string;
      detection_hints?: string[];
      priority?: number;
      actions: Array<{
        slug: string;
        title: string;
        summary?: string;
        instructions: string[];
        requires_escalation?: boolean;
      }>;
    }>;
  }>;
}

export interface ImportResult {
  categories_created: number;
  categories_updated: number;
  causes_created: number;
  causes_updated: number;
  solutions_created: number;
  solutions_updated: number;
  solutions_removed: number;
  warnings: string[];
}

// ==================== Problem Categories ====================

export const fetchCategories = async (): Promise<ProblemCategory[]> => {
  const { data } = await apiClient.get<ProblemCategory[]>(endpoints.catalogue.categories());
  return data;
};

export const fetchCategory = async (categoryId: string): Promise<ProblemCategory> => {
  const { data } = await apiClient.get<ProblemCategory>(endpoints.catalogue.category(categoryId));
  return data;
};

export const createCategory = async (payload: ProblemCategoryCreate): Promise<ProblemCategory> => {
  const { data } = await apiClient.post<ProblemCategory>(endpoints.catalogue.categories(), payload);
  return data;
};

export const updateCategory = async (
  categoryId: string,
  payload: ProblemCategoryUpdate
): Promise<ProblemCategory> => {
  const { data } = await apiClient.put<ProblemCategory>(
    endpoints.catalogue.category(categoryId),
    payload
  );
  return data;
};

export const deleteCategory = async (categoryId: string): Promise<void> => {
  await apiClient.delete(endpoints.catalogue.category(categoryId));
};

// ==================== Problem Causes ====================

export const fetchCauses = async (categoryId?: string): Promise<ProblemCause[]> => {
  const { data } = await apiClient.get<ProblemCause[]>(endpoints.catalogue.causes(), {
    params: categoryId ? { category_id: categoryId } : undefined
  });
  return data;
};

export const fetchCause = async (causeId: string): Promise<ProblemCause> => {
  const { data } = await apiClient.get<ProblemCause>(endpoints.catalogue.cause(causeId));
  return data;
};

export const createCause = async (payload: ProblemCauseCreate): Promise<ProblemCause> => {
  const { data } = await apiClient.post<ProblemCause>(endpoints.catalogue.causes(), payload);
  return data;
};

export const updateCause = async (
  causeId: string,
  payload: ProblemCauseUpdate
): Promise<ProblemCause> => {
  const { data } = await apiClient.put<ProblemCause>(endpoints.catalogue.cause(causeId), payload);
  return data;
};

export const deleteCause = async (causeId: string): Promise<void> => {
  await apiClient.delete(endpoints.catalogue.cause(causeId));
};

// ==================== Problem Solutions ====================

export const fetchSolutions = async (causeId?: string): Promise<ProblemSolution[]> => {
  const { data } = await apiClient.get<ProblemSolution[]>(endpoints.catalogue.solutions(), {
    params: causeId ? { cause_id: causeId } : undefined
  });
  return data;
};

export const fetchSolution = async (solutionId: string): Promise<ProblemSolution> => {
  const { data } = await apiClient.get<ProblemSolution>(endpoints.catalogue.solution(solutionId));
  return data;
};

export const createSolution = async (payload: ProblemSolutionCreate): Promise<ProblemSolution> => {
  const { data } = await apiClient.post<ProblemSolution>(endpoints.catalogue.solutions(), payload);
  return data;
};

export const updateSolution = async (
  solutionId: string,
  payload: ProblemSolutionUpdate
): Promise<ProblemSolution> => {
  const { data } = await apiClient.put<ProblemSolution>(
    endpoints.catalogue.solution(solutionId),
    payload
  );
  return data;
};

export const deleteSolution = async (solutionId: string): Promise<void> => {
  await apiClient.delete(endpoints.catalogue.solution(solutionId));
};

// ==================== Catalog Import ====================

export const importCatalog = async (
  catalog: TroubleshootingCatalogImport
): Promise<ImportResult> => {
  const { data } = await apiClient.post<ImportResult>(endpoints.catalogue.import(), catalog);
  return data;
};
