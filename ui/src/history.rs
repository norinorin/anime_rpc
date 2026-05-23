use std::ops::Deref;

#[derive(Debug, Clone)]
pub struct History<T> {
    current: T,
    undo_stack: Vec<T>,
    redo_stack: Vec<T>,
    max_capacity: usize,
}

impl<T: Clone> History<T> {
    pub fn new(initial: T) -> Self {
        Self::with_capacity(initial, 50)
    }

    pub fn with_capacity(initial: T, capacity: usize) -> Self {
        Self {
            current: initial,
            undo_stack: Vec::with_capacity(capacity),
            redo_stack: Vec::new(),
            max_capacity: capacity,
        }
    }

    pub fn modify<F>(&mut self, mutator: F)
    where
        F: FnOnce(&mut T),
    {
        if self.undo_stack.len() == self.max_capacity {
            self.undo_stack.remove(0);
        }

        self.undo_stack.push(self.current.clone());
        self.redo_stack.clear();
        mutator(&mut self.current)
    }

    pub fn undo(&mut self) {
        if let Some(prev) = self.undo_stack.pop() {
            self.redo_stack.push(self.current.clone());
            self.current = prev;
        }
    }

    pub fn redo(&mut self) {
        if let Some(next) = self.redo_stack.pop() {
            self.undo_stack.push(self.current.clone());
            self.current = next;
        }
    }
}

impl<T> Deref for History<T> {
    type Target = T;

    fn deref(&self) -> &Self::Target {
        &self.current
    }
}
