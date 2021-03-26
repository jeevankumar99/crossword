import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var in self.crossword.variables:
            # appends words that has to be removed from the domain set
            remove_words = []
            for words in self.domains[var]:
                if len(words) != int(var.length):
                    remove_words.append(words)
            # remove the words from the domain set using this list
            for rm_words in remove_words:
                self.domains[var].remove(rm_words)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        overlap_coordinate = self.crossword.overlaps[x, y]
        remove_words = []
        revised = False

        for x_word in self.domains[x]:
            remove = True
            for y_word in self.domains[y]:
                if x_word[overlap_coordinate[0]] == y_word[overlap_coordinate[1]]:
                    remove = False
            # if word doesn't satisfy any constraint, remove it
            if remove:
                remove_words.append(x_word)

        # remove words from x's domain that is doesn't satisfy constraints
        for words in remove_words:
            self.domains[x].remove(words)
            revised = True

        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        queue = []
        # if arcs is not passed into the function
        if arcs == None:
            for var in self.crossword.variables:
                # add arcs as (x, y) in queue, where x and y are binary constraints
                for linked_var in self.crossword.neighbors(var):
                    queue.append((var, linked_var))
        # if arcs are passed, use only those in the queue
        else:
            queue = [link for link in arcs]

        for var in queue:
            if self.revise(var[0], var[1]):
                # if x's domain is empty, return false as AC is not possible
                if len(self.domains[var[0]]) == 0:
                    return False
                # add additional arcs to queue ensure arc stays consistent
                for linked_var in (self.crossword.neighbors(var[0]) - {var[1]}):
                    queue.append((linked_var, var[0]))

        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for var in self.crossword.variables:
            if var not in assignment:
                return False
            else:
                if len(assignment[var]) == None:
                    return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # check if values are distinct
        values = list(assignment.values())
        if len(values) != len(set(values)):
            return False

        for var in assignment:
            # check the length
            if len(assignment[var]) != var.length:
                return False
            # check if values satisfy neighbor constraints
            for links in self.crossword.neighbors(var):
                overlap = self.crossword.overlaps[var, links]
                if links in assignment:
                    if assignment[var][overlap[0]] != assignment[links][overlap[1]]:
                        return False

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """

        # stores tuples (var's domain value, neighbor domain value removed count)
        sort_list = []
        for values in self.domains[var]:
            removed = 0
            for links in self.crossword.neighbors(var):
                overlap = self.crossword.overlaps[var, links]
                # iterating through domain values of each neighbor of var
                for link_values in self.domains[links]:
                    # constraint not satisfied so value should be removed in backtrack
                    if values[overlap[0]] != link_values[overlap[1]]:
                        # value to be removed count increments
                        removed += 1
            sort_list.append((values, removed))

        # sorting values in ascending order based on n
        sort_list.sort(key = lambda val: (val[1]))
        return [val for val, rem in sort_list]

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        # to store each variable and its domain length as a tuple
        temp_list = []
        for var in self.crossword.variables:
            if var not in assignment:
                temp_list.append((var, len(self.domains[var])))

        # finds the minimum domain length in the list of tuples,
        # then returns it's Variable (0th index of tuple)
        return min(temp_list, key = lambda value: (value[1]))[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment
        var = self.select_unassigned_variable(assignment)
        # get a list of domain values sorted efficiently
        for  values in self.order_domain_values(var, assignment):
            # copies dict values instead of referencing it
            new_assignment = assignment.copy()
            new_assignment[var] = values
            # checks if current dict satisfies constraints
            if self.consistent(new_assignment):
                result = self.backtrack(new_assignment)
                if result != None:
                    return result
        return None



def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
