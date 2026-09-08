import {
	Button,
	CalendarPicker,
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
	CommandDialog,
	CommandEmpty,
	CommandGroup,
	CommandInput,
	CommandItem,
	CommandList,
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogClose,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
	Input,
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
	Tabs,
	TabsContent,
	TabsList,
	TabsTrigger,
	useState,
} from "bifrost";
import { Calendar as CalendarIcon, Search } from "lucide-react";

const SELECT_OPTIONS = [
	{ label: "Draft", value: "draft" },
	{ label: "Review", value: "review" },
	{ label: "Published", value: "published" },
] as const;

const COMMAND_ITEMS = [
	"Button asChild",
	"Card",
	"Input",
	"Select",
	"Dialog",
	"CommandDialog",
	"Tabs",
	"CalendarPicker",
] as const;

export default function LegacyComponentsFixturePage() {
	const [status, setStatus] = useState("review");
	const [selectedDate, setSelectedDate] = useState<Date | undefined>(
		new Date("2026-09-06T12:00:00Z"),
	);
	const [commandOpen, setCommandOpen] = useState(false);

	return (
		<div className="mx-auto flex min-h-full w-full max-w-6xl flex-col gap-6 p-6">
			<div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
				<div className="space-y-2">
					<p className="text-sm font-medium text-muted-foreground">
						Inline v1 compatibility fixture
					</p>
					<h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
						Design Review Legacy Components
					</h1>
					<p className="max-w-3xl text-sm text-muted-foreground">
						This page exercises the published v1 import surface for
						Button asChild, Card, Input, Select, Dialog,
						CommandDialog, Tabs, and CalendarPicker.
					</p>
				</div>
				<Button asChild variant="outline">
					<a href="#details">Jump to details</a>
				</Button>
			</div>

			<Tabs defaultValue="overview" className="w-full">
				<TabsList className="flex w-full flex-wrap justify-start">
					<TabsTrigger value="overview">Overview</TabsTrigger>
					<TabsTrigger value="forms">Form controls</TabsTrigger>
					<TabsTrigger value="calendar">Calendar</TabsTrigger>
				</TabsList>

				<TabsContent value="overview" className="mt-6 space-y-6">
					<div className="grid gap-6 lg:grid-cols-2">
						<Card>
							<CardHeader>
								<CardTitle>Route shell</CardTitle>
								<CardDescription>
									The live app should render from the real V1
									host bundle, not a separate harness.
								</CardDescription>
							</CardHeader>
							<CardContent className="space-y-4">
								<p className="text-sm text-muted-foreground">
									Use the controls below to confirm the
									imported primitives still behave as the
									platform contract expects.
								</p>
								<div className="flex flex-wrap gap-2">
									<Button onClick={() => setCommandOpen(true)}>
										<Search className="mr-2 h-4 w-4" />
										Open command dialog
									</Button>
									<Dialog>
										<DialogTrigger asChild>
											<Button variant="outline">
												Open dialog
											</Button>
										</DialogTrigger>
										<DialogContent>
											<DialogHeader>
												<DialogTitle>
													Legacy components
												</DialogTitle>
												<DialogDescription>
													Dialog content confirms the
													v1 wrapper exports.
												</DialogDescription>
											</DialogHeader>
											<DialogFooter>
												<DialogClose asChild>
													<Button variant="secondary">
														Close
													</Button>
												</DialogClose>
											</DialogFooter>
										</DialogContent>
									</Dialog>
								</div>
							</CardContent>
						</Card>

						<Card id="details">
							<CardHeader>
								<CardTitle>Published alias contract</CardTitle>
								<CardDescription>
									These names must resolve from{" "}
									<code className="font-mono">"bifrost"</code>.
								</CardDescription>
							</CardHeader>
							<CardContent>
								<ul className="grid gap-2 text-sm text-muted-foreground sm:grid-cols-2">
									{COMMAND_ITEMS.map((item) => (
										<li key={item} className="rounded-md border bg-muted/30 px-3 py-2">
											{item}
										</li>
									))}
								</ul>
							</CardContent>
							<CardFooter className="text-sm text-muted-foreground">
								Preview route: /apps/design-review-legacy-components
							</CardFooter>
						</Card>
					</div>
				</TabsContent>

				<TabsContent value="forms" className="mt-6">
					<div className="grid gap-6 lg:grid-cols-2">
						<Card>
							<CardHeader>
								<CardTitle>Inputs and select</CardTitle>
								<CardDescription>
									Representative form controls rendered in a
									v1 page.
								</CardDescription>
							</CardHeader>
							<CardContent className="space-y-4">
								<div className="space-y-2">
									<label htmlFor="fixture-name" className="text-sm font-medium">
										Fixture name
									</label>
									<Input
										id="fixture-name"
										defaultValue="Legacy Components"
										placeholder="Fixture name"
									/>
								</div>
								<div className="space-y-2">
									<label htmlFor="fixture-status" className="text-sm font-medium">
										Status
									</label>
									<Select value={status} onValueChange={setStatus}>
										<SelectTrigger id="fixture-status">
											<SelectValue placeholder="Choose a status" />
										</SelectTrigger>
										<SelectContent>
											{SELECT_OPTIONS.map((option) => (
												<SelectItem key={option.value} value={option.value}>
													{option.label}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</div>
								<p className="text-sm text-muted-foreground">
									Selected status: <span className="font-medium text-foreground">{status}</span>
								</p>
							</CardContent>
						</Card>

						<Card>
							<CardHeader>
								<CardTitle>Command dialog palette</CardTitle>
								<CardDescription>
									Uses the wrapped CommandDialog export from
									the v1 host surface.
								</CardDescription>
							</CardHeader>
							<CardContent className="space-y-4">
								<p className="text-sm text-muted-foreground">
									Click the button below to open the palette.
								</p>
								<Button onClick={() => setCommandOpen(true)} variant="secondary">
									<Search className="mr-2 h-4 w-4" />
									Open CommandDialog
								</Button>
							</CardContent>
						</Card>
					</div>
				</TabsContent>

				<TabsContent value="calendar" className="mt-6">
					<div className="grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)]">
						<Card>
							<CardHeader>
								<CardTitle>Calendar picker</CardTitle>
								<CardDescription>
									CalendarPicker should resolve to the shadcn
									date picker alias, while Calendar remains the
									Lucide icon.
								</CardDescription>
							</CardHeader>
							<CardContent className="space-y-4">
								<div className="flex items-center gap-2 text-sm text-muted-foreground">
									<CalendarIcon className="h-4 w-4" />
									<span>
										Selected date:{" "}
										<span className="font-medium text-foreground">
											{selectedDate?.toDateString()}
										</span>
									</span>
								</div>
								<CalendarPicker
									mode="single"
									selected={selectedDate}
									onSelect={(date) => setSelectedDate(date ?? undefined)}
								/>
							</CardContent>
						</Card>

						<Card>
							<CardHeader>
								<CardTitle>Notes</CardTitle>
								<CardDescription>
									The live route is publishable once the seed
									app is created.
								</CardDescription>
							</CardHeader>
							<CardContent className="space-y-3 text-sm text-muted-foreground">
								<p>
									The fixture should compile in the real V1
									bundle and keep the published import alias
									contract intact.
								</p>
								<p>
									Use the companion command note to recreate
									the app in the seeded debug instance.
								</p>
							</CardContent>
						</Card>
					</div>
				</TabsContent>
			</Tabs>

			<CommandDialog open={commandOpen} onOpenChange={setCommandOpen}>
				<CommandInput placeholder="Search legacy components..." />
				<CommandList>
					<CommandEmpty>No components found.</CommandEmpty>
					<CommandGroup heading="Legacy imports">
						{COMMAND_ITEMS.map((item) => (
							<CommandItem key={item} onSelect={() => setCommandOpen(false)}>
								{item}
							</CommandItem>
						))}
					</CommandGroup>
				</CommandList>
			</CommandDialog>
		</div>
	);
}
