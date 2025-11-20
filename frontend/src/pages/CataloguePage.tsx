import { useCallback, useEffect, useState } from "react";
import Modal from "../components/catalogue/Modal";
import CategoryForm from "../components/catalogue/CategoryForm";
import CauseForm from "../components/catalogue/CauseForm";
import SolutionForm from "../components/catalogue/SolutionForm";
import {
  fetchCategories,
  fetchCauses,
  fetchSolutions,
  createCategory,
  updateCategory,
  deleteCategory,
  createCause,
  updateCause,
  deleteCause,
  createSolution,
  updateSolution,
  deleteSolution,
  importCatalog,
  type ProblemCategory,
  type ProblemCause,
  type ProblemSolution,
  type ProblemCategoryCreate,
  type ProblemCategoryUpdate,
  type ProblemCauseCreate,
  type ProblemCauseUpdate,
  type ProblemSolutionCreate,
  type ProblemSolutionUpdate,
  type TroubleshootingCatalogImport
} from "../api/catalogue";

type ModalState =
  | { type: "closed" }
  | { type: "create-category" }
  | { type: "edit-category"; category: ProblemCategory }
  | { type: "create-cause"; categoryId: string }
  | { type: "edit-cause"; cause: ProblemCause }
  | { type: "create-solution"; causeId: string }
  | { type: "edit-solution"; solution: ProblemSolution }
  | { type: "import" };

const CataloguePage = () => {
  const [categories, setCategories] = useState<ProblemCategory[]>([]);
  const [allCauses, setAllCauses] = useState<ProblemCause[]>([]);
  const [allSolutions, setAllSolutions] = useState<ProblemSolution[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<ProblemCategory | null>(null);
  const [selectedCause, setSelectedCause] = useState<ProblemCause | null>(null);
  const [modalState, setModalState] = useState<ModalState>({ type: "closed" });
  const [isLoading, setIsLoading] = useState(false);
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [importJson, setImportJson] = useState("");

  const showNotification = (type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4000);
  };

  const loadCategories = useCallback(async () => {
    setIsLoading(true);
    try {
      const [categoriesData, causesData, solutionsData] = await Promise.all([
        fetchCategories(),
        fetchCauses(),
        fetchSolutions()
      ]);
      setCategories(categoriesData);
      setAllCauses(causesData);
      setAllSolutions(solutionsData);
    } catch (error) {
      showNotification("error", "Failed to load catalogue data");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  }, []);



  useEffect(() => {
    void loadCategories();
  }, [loadCategories]);

  useEffect(() => {
    if (!selectedCategory) {
      setSelectedCause(null);
    }
  }, [selectedCategory]);

  const handleCreateCategory = async (data: ProblemCategoryCreate) => {
    try {
      await createCategory(data);
      showNotification("success", "Category created successfully");
      setModalState({ type: "closed" });
      void loadCategories();
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Failed to create category";
      showNotification("error", message);
      throw error;
    }
  };

  const handleUpdateCategory = async (data: ProblemCategoryUpdate) => {
    if (modalState.type !== "edit-category") return;
    try {
      await updateCategory(modalState.category.id, data);
      showNotification("success", "Category updated successfully");
      setModalState({ type: "closed" });
      void loadCategories();
      if (selectedCategory?.id === modalState.category.id) {
        setSelectedCategory(null);
      }
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Failed to update category";
      showNotification("error", message);
      throw error;
    }
  };

  const handleDeleteCategory = async (categoryId: string) => {
    if (!confirm("Are you sure you want to delete this category? All causes and solutions will also be deleted.")) {
      return;
    }
    try {
      await deleteCategory(categoryId);
      showNotification("success", "Category deleted successfully");
      void loadCategories();
      if (selectedCategory?.id === categoryId) {
        setSelectedCategory(null);
      }
    } catch (error: unknown) {
      let message = "Failed to delete category";
      if (error && typeof error === "object" && "response" in error) {
        const response = (error as { response?: { data?: { detail?: string } } }).response;
        if (response?.data?.detail) {
          message = response.data.detail;
        }
      }
      showNotification("error", message);
    }
  };

  const handleCreateCause = async (data: ProblemCauseCreate) => {
    try {
      await createCause(data);
      showNotification("success", "Cause created successfully");
      setModalState({ type: "closed" });
      void loadCategories();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to create cause";
      showNotification("error", message);
      throw error;
    }
  };

  const handleUpdateCause = async (data: ProblemCauseUpdate) => {
    if (modalState.type !== "edit-cause") return;
    try {
      await updateCause(modalState.cause.id, data);
      showNotification("success", "Cause updated successfully");
      setModalState({ type: "closed" });
      void loadCategories();
      if (selectedCause?.id === modalState.cause.id) {
        setSelectedCause(null);
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to update cause";
      showNotification("error", message);
      throw error;
    }
  };

  const handleDeleteCause = async (causeId: string) => {
    if (!confirm("Are you sure you want to delete this cause? All solutions will also be deleted.")) {
      return;
    }
    try {
      await deleteCause(causeId);
      showNotification("success", "Cause deleted successfully");
      void loadCategories();
      if (selectedCause?.id === causeId) {
        setSelectedCause(null);
      }
    } catch (error: unknown) {
      let message = "Failed to delete cause";
      if (error && typeof error === "object" && "response" in error) {
        const response = (error as { response?: { data?: { detail?: string } } }).response;
        if (response?.data?.detail) {
          message = response.data.detail;
        }
      }
      showNotification("error", message);
    }
  };

  const handleCreateSolution = async (data: ProblemSolutionCreate) => {
    try {
      await createSolution(data);
      showNotification("success", "Solution created successfully");
      setModalState({ type: "closed" });
      void loadCategories();
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Failed to create solution";
      showNotification("error", message);
      throw error;
    }
  };

  const handleUpdateSolution = async (data: ProblemSolutionUpdate) => {
    if (modalState.type !== "edit-solution") return;
    try {
      await updateSolution(modalState.solution.id, data);
      showNotification("success", "Solution updated successfully");
      setModalState({ type: "closed" });
      void loadCategories();
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Failed to update solution";
      showNotification("error", message);
      throw error;
    }
  };

  const handleDeleteSolution = async (solutionId: string) => {
    if (!confirm("Are you sure you want to delete this solution?")) {
      return;
    }
    try {
      await deleteSolution(solutionId);
      showNotification("success", "Solution deleted successfully");
      void loadCategories();
    } catch (error: unknown) {
      let message = "Failed to delete solution";
      if (error && typeof error === "object" && "response" in error) {
        const response = (error as { response?: { data?: { detail?: string } } }).response;
        if (response?.data?.detail) {
          message = response.data.detail;
        }
      }
      showNotification("error", message);
    }
  };

  const handleImport = async () => {
    try {
      const catalog: TroubleshootingCatalogImport = JSON.parse(importJson);
      const result = await importCatalog(catalog);
      showNotification(
        "success",
        `Import successful: ${result.categories_created} categories created, ${result.causes_created} causes created, ${result.solutions_created} solutions created`
      );
      setModalState({ type: "closed" });
      setImportJson("");
      void loadCategories();
      setSelectedCategory(null);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to import catalog";
      showNotification("error", message);
    }
  };

  const getCausesForCategory = (categoryId: string) => {
    return allCauses.filter((c) => c.category_id === categoryId);
  };

  const getSolutionsForCause = (causeId: string) => {
    return allSolutions.filter((s) => s.cause_id === causeId);
  };

  return (
    <div className="mx-auto flex w-full max-w-[1600px] flex-1 flex-col gap-6 px-4 py-6 sm:px-6 lg:px-10">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-white">Troubleshooting Catalogue</h1>
          <p className="text-sm text-white/60">
            Manage problem categories, causes, and solutions
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => setModalState({ type: "import" })}
            className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-brand-accent hover:text-brand-accent"
          >
            Import JSON
          </button>
          <button
            type="button"
            onClick={() => setModalState({ type: "create-category" })}
            className="rounded-full bg-brand-accent px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-brand-accent/40 transition hover:bg-brand-accentHover"
          >
            + New Category
          </button>
        </div>
      </div>

      {/* Notification */}
      {notification && (
        <div
          className={`rounded-lg border px-4 py-3 ${
            notification.type === "success"
              ? "border-green-500/30 bg-green-500/10 text-green-400"
              : "border-red-500/30 bg-red-500/10 text-red-400"
          }`}
        >
          {notification.message}
        </div>
      )}

      {/* Horizontal Category Selector */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Categories ({categories.length})</h2>
        </div>

        {isLoading && categories.length === 0 ? (
          <div className="flex h-20 items-center justify-center rounded-lg border border-brand-border bg-brand-surface">
            <p className="text-sm text-white/50">Loading categories...</p>
          </div>
        ) : categories.length === 0 ? (
          <div className="flex h-20 items-center justify-center rounded-lg border border-brand-border bg-brand-surface">
            <p className="text-sm text-white/50">No categories yet. Create one to get started.</p>
          </div>
        ) : (
          <div className="relative">
            <div className="flex gap-3 overflow-x-auto pb-3 pr-8 pt-2" style={{
              scrollbarWidth: 'thin',
              scrollbarColor: '#FF5641 transparent'
            }}>
              {categories.map((category) => {
                const categoryHasCauses = getCausesForCategory(category.id).length > 0;
                return (
                <button
                  key={category.id}
                  onClick={() =>
                    setSelectedCategory(
                      selectedCategory?.id === category.id ? null : category
                    )
                  }
                  className={`group relative flex-shrink-0 rounded-xl border px-5 py-4 shadow-lg transition-all ${
                    selectedCategory?.id === category.id
                      ? "border-brand-accent bg-gradient-to-br from-brand-accent/20 to-brand-accent/5 shadow-brand-accent/30"
                      : "border-brand-border bg-gradient-to-br from-brand-surface to-brand-surfaceAlt hover:border-brand-accent/50 hover:shadow-brand-accent/20"
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <div className="text-left min-w-[180px]">
                      <h3 className="font-semibold text-white text-base">{category.name}</h3>
                      <p className="mt-0.5 text-xs font-mono text-white/50">{category.slug}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                        selectedCategory?.id === category.id
                          ? "bg-brand-accent/30 text-brand-accent"
                          : "bg-white/10 text-white/70"
                      }`}>
                        {getCausesForCategory(category.id).length} causes
                      </span>
                      <div className="flex gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setModalState({ type: "edit-category", category });
                          }}
                          className="rounded-lg p-1.5 text-white/60 transition hover:bg-white/10 hover:text-brand-accent"
                          title="Edit"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteCategory(category.id);
                          }}
                          disabled={categoryHasCauses}
                          className="rounded-lg p-1.5 text-white/60 transition hover:bg-red-500/20 hover:text-red-400 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-white/60"
                          title={categoryHasCauses ? "Cannot delete: category has causes" : "Delete"}
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                </button>
                );
              })}
            </div>
            {/* Fade effect at the end */}
            <div className="pointer-events-none absolute right-0 top-0 h-full w-16 bg-gradient-to-l from-brand-background to-transparent" />
          </div>
        )}
      </div>

      {/* Expandable Causes and Solutions */}
      {selectedCategory && (
        <div className="space-y-6 rounded-xl border border-brand-border bg-brand-surface/50 p-6">
          {/* Category Info Header */}
          <div className="border-b border-white/10 pb-4">
            <h2 className="text-xl font-semibold text-white">{selectedCategory.name}</h2>
            {selectedCategory.description && (
              <p className="mt-1 text-sm text-white/60">{selectedCategory.description}</p>
            )}
          </div>

          {/* Causes Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Causes ({getCausesForCategory(selectedCategory.id).length})</h3>
              <button
                type="button"
                onClick={() =>
                  setModalState({ type: "create-cause", categoryId: selectedCategory.id })
                }
                className="rounded-lg bg-brand-accent px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-brand-accentHover"
              >
                + Add Cause
              </button>
            </div>

            {getCausesForCategory(selectedCategory.id).length === 0 ? (
              <div className="flex h-24 items-center justify-center rounded-lg border border-dashed border-white/20">
                <p className="text-sm text-white/50">No causes yet. Add one to get started.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {getCausesForCategory(selectedCategory.id).map((cause) => {
                  const isExpanded = selectedCause?.id === cause.id;
                  const causeSolutions = getSolutionsForCause(cause.id);

                  return (
                    <div
                      key={cause.id}
                      className={`rounded-lg border transition ${
                        isExpanded
                          ? "border-brand-accent bg-brand-accent/5"
                          : "border-brand-border bg-brand-surface"
                      }`}
                    >
                      {/* Cause Header */}
                      <div
                        onClick={() => setSelectedCause(isExpanded ? null : cause)}
                        className="flex cursor-pointer items-center justify-between gap-3 p-4"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h4 className="font-semibold text-white">{cause.name}</h4>
                            <span className="rounded-full bg-brand-accent/20 px-2 py-0.5 text-xs font-medium text-brand-accent">
                              Priority: {cause.default_priority}
                            </span>
                            <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/70">
                              {causeSolutions.length} {causeSolutions.length === 1 ? "solution" : "solutions"}
                            </span>
                          </div>
                          <p className="mt-0.5 text-xs font-mono text-white/50">{cause.slug}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setModalState({ type: "edit-cause", cause });
                            }}
                            className="rounded p-1.5 text-white/60 transition hover:bg-white/10 hover:text-brand-accent"
                            title="Edit cause"
                          >
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteCause(cause.id);
                            }}
                            disabled={causeSolutions.length > 0}
                            className="rounded p-1.5 text-white/60 transition hover:bg-red-500/20 hover:text-red-400 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent disabled:hover:text-white/60"
                            title={causeSolutions.length > 0 ? "Cannot delete: cause has solutions" : "Delete cause"}
                          >
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                          <svg
                            className={`h-5 w-5 text-white/60 transition-transform ${
                              isExpanded ? "rotate-90" : ""
                            }`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </div>
                      </div>

                      {/* Expanded Solutions */}
                      {isExpanded && (
                        <div className="border-t border-white/10 p-4 pt-3">
                          <div className="mb-3 flex items-center justify-between">
                            <h5 className="text-sm font-semibold text-white">
                              Solutions ({causeSolutions.length})
                            </h5>
                            <button
                              type="button"
                              onClick={() =>
                                setModalState({ type: "create-solution", causeId: cause.id })
                              }
                              className="rounded-lg bg-brand-accent px-2.5 py-1 text-xs font-semibold text-white transition hover:bg-brand-accentHover"
                            >
                              + Add Solution
                            </button>
                          </div>

                          {causeSolutions.length === 0 ? (
                            <div className="flex h-16 items-center justify-center rounded-lg border border-dashed border-white/20">
                              <p className="text-xs text-white/50">No solutions yet</p>
                            </div>
                          ) : (
                            <div className="space-y-2">
                              {causeSolutions.map((solution) => (
                                <div
                                  key={solution.id}
                                  className="rounded-lg border border-white/10 bg-brand-surface/50 p-3"
                                >
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="flex-1">
                                      <div className="flex items-center gap-2 flex-wrap">
                                        <h6 className="text-sm font-semibold text-white">
                                          {solution.title}
                                        </h6>
                                        {solution.requires_escalation && (
                                          <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-xs font-medium text-red-400">
                                            Escalation
                                          </span>
                                        )}
                                        <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-white/60">
                                          Step {solution.step_order}
                                        </span>
                                      </div>
                                      <p className="mt-0.5 text-xs font-mono text-white/50">
                                        {solution.slug}
                                      </p>
                                      {solution.summary && (
                                        <p className="mt-2 text-xs text-white/70">{solution.summary}</p>
                                      )}
                                      <div className="mt-2">
                                        <p className="text-xs font-medium text-white/60">Instructions:</p>
                                        <p className="mt-1 text-xs text-white/60 line-clamp-2">
                                          {solution.instructions}
                                        </p>
                                      </div>
                                    </div>
                                    <div className="flex gap-1">
                                      <button
                                        onClick={() =>
                                          setModalState({ type: "edit-solution", solution })
                                        }
                                        className="rounded p-1 text-white/60 transition hover:bg-white/10 hover:text-brand-accent"
                                        title="Edit solution"
                                      >
                                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                        </svg>
                                      </button>
                                      <button
                                        onClick={() => handleDeleteSolution(solution.id)}
                                        className="rounded p-1 text-white/60 transition hover:bg-red-500/20 hover:text-red-400"
                                        title="Delete solution"
                                      >
                                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                        </svg>
                                      </button>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modals */}
      <Modal
        isOpen={modalState.type === "create-category"}
        onClose={() => setModalState({ type: "closed" })}
        title="Create Category"
      >
        <CategoryForm
          onSubmit={(data) => handleCreateCategory(data as ProblemCategoryCreate)}
          onCancel={() => setModalState({ type: "closed" })}
        />
      </Modal>

      <Modal
        isOpen={modalState.type === "edit-category"}
        onClose={() => setModalState({ type: "closed" })}
        title="Edit Category"
      >
        {modalState.type === "edit-category" && (
          <CategoryForm
            category={modalState.category}
            onSubmit={(data) => handleUpdateCategory(data as ProblemCategoryUpdate)}
            onCancel={() => setModalState({ type: "closed" })}
          />
        )}
      </Modal>

      <Modal
        isOpen={modalState.type === "create-cause"}
        onClose={() => setModalState({ type: "closed" })}
        title="Create Cause"
      >
        {modalState.type === "create-cause" && (
          <CauseForm
            categoryId={modalState.categoryId}
            onSubmit={(data) => handleCreateCause(data as ProblemCauseCreate)}
            onCancel={() => setModalState({ type: "closed" })}
          />
        )}
      </Modal>

      <Modal
        isOpen={modalState.type === "edit-cause"}
        onClose={() => setModalState({ type: "closed" })}
        title="Edit Cause"
      >
        {modalState.type === "edit-cause" && (
          <CauseForm
            cause={modalState.cause}
            categoryId={modalState.cause.category_id}
            onSubmit={(data) => handleUpdateCause(data as ProblemCauseUpdate)}
            onCancel={() => setModalState({ type: "closed" })}
          />
        )}
      </Modal>

      <Modal
        isOpen={modalState.type === "create-solution"}
        onClose={() => setModalState({ type: "closed" })}
        title="Create Solution"
      >
        {modalState.type === "create-solution" && (
          <SolutionForm
            causeId={modalState.causeId}
            onSubmit={(data) => handleCreateSolution(data as ProblemSolutionCreate)}
            onCancel={() => setModalState({ type: "closed" })}
          />
        )}
      </Modal>

      <Modal
        isOpen={modalState.type === "edit-solution"}
        onClose={() => setModalState({ type: "closed" })}
        title="Edit Solution"
      >
        {modalState.type === "edit-solution" && (
          <SolutionForm
            solution={modalState.solution}
            causeId={modalState.solution.cause_id}
            onSubmit={(data) => handleUpdateSolution(data as ProblemSolutionUpdate)}
            onCancel={() => setModalState({ type: "closed" })}
          />
        )}
      </Modal>

      <Modal
        isOpen={modalState.type === "import"}
        onClose={() => {
          setModalState({ type: "closed" });
          setImportJson("");
        }}
        title="Import Troubleshooting Catalog"
      >
        <div className="space-y-4">
          <div>
            <label htmlFor="import-json" className="mb-1 block text-sm font-medium text-white/80">
              Paste JSON Catalog
            </label>
            <textarea
              id="import-json"
              value={importJson}
              onChange={(e) => setImportJson(e.target.value)}
              rows={15}
              className="w-full rounded-lg border border-brand-border bg-brand-surface px-3 py-2 font-mono text-sm text-white placeholder-white/40 transition focus:border-brand-accent focus:outline-none"
              placeholder='{"version": "1.0", "problems": [...]}'
            />
          </div>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => {
                setModalState({ type: "closed" });
                setImportJson("");
              }}
              className="rounded-lg border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-white/30"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleImport}
              className="rounded-lg bg-brand-accent px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-brand-accent/40 transition hover:bg-brand-accentHover"
            >
              Import
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default CataloguePage;
